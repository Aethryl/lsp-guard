<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/logo-dark.svg">
    <img src=".github/logo-light.svg" alt="lsp-guard" width="255" height="64">
  </picture>
</p>

<p align="center">
  A Claude Code plugin that makes the agent read source code through the language server
  instead of <code>cat</code> and <code>sed</code>.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

## What it does

Agents tend to read a whole file to find one function. On a 1,000-line file that costs
thousands of tokens; an outline from `documentSymbol` plus a ranged Read costs a few hundred.
lsp-guard is a `PreToolUse` hook that pushes the agent toward the second option:

- **Denies** `cat`, `sed`, `head`, `tail`, `less`, `more`, `bat` and `nl` on a source file,
  including through the `rtk` wrapper. Writes pass: a command containing a heredoc, `sed -i`
  and output redirects (`>`) are allowed, as are these tools on piped input
  (`git show HEAD:app.py | head`).
- **Denies** a Read of a whole source file over 300 lines and tells the agent to outline it
  with `documentSymbol` first. A Read with `offset` or `limit` always passes.
- **Reminds** the agent to use `findReferences` or `workspaceSymbol` when it greps source,
  through `grep`/`rg`/`egrep` or the Grep tool. This is a hint, not a denial.

The same rules apply to subagents, which have the LSP tool too.

## Install

Needs `python3` on PATH (3.9+).

```text
/plugin marketplace add Aethryl/lsp-guard
/plugin install lsp-guard@lsp-guard
```

lsp-guard only points the agent at the LSP tool; it doesn't provide one. Install an LSP
plugin for each language you want guarded:

| Language | Extensions | Server on PATH | LSP plugin |
|---|---|---|---|
| Python | `.py` `.pyi` | `ty`, `pyright-langserver` or `pylsp` | [ty-agent-lsp](https://github.com/Aethryl/ty-agent-lsp) or `pyright-lsp` |
| Rust | `.rs` | `rust-analyzer` | `rust-analyzer-lsp` |
| TypeScript / JavaScript | `.ts` `.tsx` `.mts` `.cts` `.js` `.jsx` `.mjs` `.cjs` | `typescript-language-server` | `typescript-lsp` |

A language is guarded only when one of its servers is on PATH. Files in other languages are
left alone.

## Usage

Nothing to configure. Once installed, the hook runs before every Bash, Read and Grep call.
When it denies a call, the agent gets the reason and a suggestion, for example:

```text
service.py has 1240 lines. Outline it first with LSP documentSymbol, then Read the
symbol's range with offset/limit. Pass an explicit offset/limit if you really need the
whole file.
```

If you do need the whole file, ask for it: the agent can pass an explicit offset/limit.

## How it works

[`hooks.json`](plugins/lsp-guard/hooks/hooks.json) registers [`hooks/lsp_guard.py`](plugins/lsp-guard/hooks/lsp_guard.py)
as a `PreToolUse` hook on `Bash|Read|Grep`. The script uses only the Python standard library:

1. It checks which language servers are on PATH (`shutil.which`) and builds the list of
   guarded extensions from them.
2. For Bash, it splits the command on `;`, `&&`, `||`, `|` and newlines, and checks each
   segment's program and arguments.
3. For Read, it counts the file's lines when no offset or limit is given.
4. It answers with a `deny` decision or with `additionalContext`, or prints nothing to let
   the call through.

### Limits

- It checks for servers on PATH, not whether the matching LSP plugin is enabled.
- A server installed only inside a project's virtualenv isn't found.
- Command parsing is pattern-based, not a full shell parser, so unusual commands can slip
  through or be caught.

## Licence

[MIT](LICENSE)
