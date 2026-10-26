#!/usr/bin/env python3
"""PreToolUse guard that steers source reading toward the language server.

For every language whose server is on PATH:
  * Bash `cat`/`sed`/`head`/`tail`/`less`/`bat` on a source file is denied: use Read or LSP.
  * Read of a source file over READ_LIMIT lines without offset/limit is denied: outline first.
  * grep/rg (Bash or the Grep tool) over that language gets a reminder to use the LSP.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import sys
from functools import cache
from pathlib import Path
from typing import NamedTuple

READ_LIMIT = 300
VIEWERS = {"cat", "sed", "head", "tail", "less", "more", "bat", "nl"}
SEARCHERS = {"grep", "rg", "egrep"}
SEPARATORS = re.compile(r"&&|\|\||[;|\n]")


class Language(NamedTuple):
    extensions: tuple[str, ...]
    servers: tuple[str, ...]
    search_types: tuple[str, ...]


LANGUAGES = (
    Language((".py", ".pyi"), ("ty", "pyright-langserver", "pylsp"), ("py",)),
    Language((".rs",), ("rust-analyzer",), ("rust",)),
    Language(
        (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"),
        ("typescript-language-server",),
        ("ts", "js"),
    ),
)

DENY_BASH = (
    "Don't read source through {tool}. Use the LSP tool (documentSymbol to outline the file, "
    "hover/goToDefinition for one symbol), then Read with offset/limit for the lines you need."
)
DENY_READ = (
    "{path} has {lines} lines. Outline it first with LSP documentSymbol, then Read the symbol's "
    "range with offset/limit. Pass an explicit offset/limit if you really need the whole file."
)
NUDGE_SEARCH = (
    "If the pattern is a symbol name, use LSP findReferences or workspaceSymbol instead. "
    "Grep is for strings, comments, dynamic access and files without a language server."
)


@cache
def guarded() -> tuple[Language, ...]:
    return tuple(
        lang for lang in LANGUAGES if any(shutil.which(s) for s in lang.servers)
    )


@cache
def source_pattern() -> re.Pattern[str] | None:
    extensions = [re.escape(ext) for lang in guarded() for ext in lang.extensions]
    return re.compile(rf"({'|'.join(extensions)})$") if extensions else None


@cache
def search_pattern() -> re.Pattern[str] | None:
    extensions = [re.escape(ext) for lang in guarded() for ext in lang.extensions]
    types = [t for lang in guarded() for t in lang.search_types]
    if not extensions:
        return None
    exts, kinds = "|".join(extensions), "|".join(types)
    return re.compile(rf"(--type[= ](?:{kinds})\b|-t ?(?:{kinds})\b|(?:{exts})\b)")


def is_source(path: str) -> bool:
    pattern = source_pattern()
    return bool(pattern and pattern.search(path))


def respond(**fields: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **fields}}))


def deny(reason: str) -> None:
    respond(permissionDecision="deny", permissionDecisionReason=reason)


def words(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def check_bash(command: str) -> None:
    if "<<" in command:
        return
    searching = search_pattern()
    for segment in SEPARATORS.split(command):
        argv = words(segment)
        if not argv:
            continue
        tool = Path(argv[0]).name
        if tool == "rtk" and len(argv) > 1:
            tool, argv = argv[1], argv[1:]
        viewing = tool in VIEWERS and ">" not in segment and "-i" not in argv[1:]
        if viewing and any(is_source(arg) for arg in argv[1:]):
            deny(DENY_BASH.format(tool=tool))
            return
        if tool in SEARCHERS and searching and searching.search(segment):
            respond(additionalContext=NUDGE_SEARCH)
            return


def check_read(tool_input: dict) -> None:
    path = tool_input.get("file_path", "")
    if not is_source(path) or tool_input.get("offset") or tool_input.get("limit"):
        return
    try:
        with open(path, "rb") as handle:
            lines = sum(1 for _ in handle)
    except OSError:
        return
    if lines > READ_LIMIT:
        deny(DENY_READ.format(path=Path(path).name, lines=lines))


def check_grep(tool_input: dict) -> None:
    searching = search_pattern()
    scope = " ".join(
        f"{flag} {tool_input[key]}"
        for key, flag in (("type", "--type"), ("glob", ""), ("path", ""))
        if tool_input.get(key)
    )
    if searching and searching.search(scope):
        respond(additionalContext=NUDGE_SEARCH)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    tool, tool_input = event.get("tool_name"), event.get("tool_input") or {}
    if tool == "Bash":
        check_bash(tool_input.get("command", ""))
    elif tool == "Read":
        check_read(tool_input)
    elif tool == "Grep":
        check_grep(tool_input)


if __name__ == "__main__":
    main()
