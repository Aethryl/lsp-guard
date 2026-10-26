# lsp-guard

A Claude Code hook that steers the agent to the language server instead of reading source
through the shell. Reading a 1,000-line file to find one function costs thousands of tokens;
`documentSymbol` plus a ranged Read costs a few hundred.

## Install

```
/plugin marketplace add Aethryl/lsp-guard
/plugin install lsp-guard@lsp-guard
```

Pair it with an LSP plugin per language, or the guard has nothing to point the agent at:

| Language | Extensions | Server on PATH | LSP plugin |
|---|---|---|---|
| Python | `.py` `.pyi` | `ty`, `pyright-langserver` or `pylsp` | `ty-agent-lsp` or `pyright-lsp` |
| Rust | `.rs` | `rust-analyzer` | `rust-analyzer-lsp` |
| TypeScript / JavaScript | `.ts` `.tsx` `.mts` `.cts` `.js` `.jsx` `.mjs` `.cjs` | `typescript-language-server` | `typescript-lsp` |

A language is only guarded when one of its servers is on PATH.

## What it does

- **Denies** `cat`, `sed`, `head`, `tail`, `less`, `bat` and `nl` on a source file. Writes
  through a heredoc, `sed -i` and piped command output pass.
- **Denies** a whole-file Read of a source file over 300 lines until the agent outlines it
  with `documentSymbol` and reads a range. An explicit offset/limit always passes.
- **Reminds** the agent to use `findReferences` or `workspaceSymbol` when it greps source.

## Limits

It detects servers on PATH, not whether the matching LSP plugin is enabled. A server
installed only inside a project's virtualenv is not seen.

## License

MIT
