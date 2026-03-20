# ContextMate

**Semantic code search for Claude Code.** Index your codebase into meaningful
chunks, return only what matters — with layered context that includes
dependencies, file signatures, and a repo map. Local embeddings. No API keys.
No cloud.

Supports **Python, JavaScript, TypeScript, Rust, Go, Java, C, C++, Ruby, and C#**.

```
source code --> tree-sitter (parse) --> Ollama (embed) --> ChromaDB (store)
                                                               |
                                          query + 4-layer context assembly
                                                               |
                                                               v
                                               repo map + file context +
                                            dependency graph + matched chunks
                                                     --> Claude
```

---

## Why ContextMate

Dumping entire files into context wastes tokens. Most of the code you load
is irrelevant to the question being asked. ContextMate fixes this by:

- **Parsing your code semantically** — tree-sitter extracts functions, classes,
  and definitions as individual chunks, not arbitrary line ranges.
- **Returning layered context** — you don't just get matching code. You get the
  repo map, file-level imports and signatures, dependency relationships, and
  then the actual chunks. Four layers, token-budgeted.
- **Staying local** — embeddings run through Ollama on your machine. Nothing
  leaves your network.

### Benchmark

Tested on a 15-file TypeScript backend (~1,600 lines). Query: "how does
authentication work?"

| | Characters | Approx. tokens |
|---|---|---|
| Without ContextMate (read all files) | 49,705 | ~12,426 |
| With ContextMate (top 10 chunks) | 3,612 | ~903 |
| **Reduction** | | **93%** |

ContextMate returned 10 targeted chunks from `oauth.ts`, `middleware.ts`,
`user.ts`, and `notification.ts` — the files that actually deal with auth.
The other 11 files were never loaded into context.

---

## One-Command Setup

Paste this into Claude Code. It walks through every step, checks for errors,
and sets up the MCP server and project config for you.

```
Set up ContextMate, a local MCP server that gives you semantic code search
with layered context. Follow these steps in order. Run each command, check
the output, and only move on when it succeeds. If something fails, diagnose
and fix it before continuing.

STEP 1 -- CHECK PYTHON

Run: python3 --version

Need 3.11 or newer. If it's missing or too old:
  - macOS: brew install python3
    (install Homebrew first if needed:
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)")
  - Linux/WSL: sudo apt install python3 python3-venv
    (or the equivalent for your distro)

Confirm python3 >= 3.11 works, then also confirm venv is available:
  Run: python3 -m venv --help
  If that fails on Linux: sudo apt install python3-venv

STEP 2 -- CHECK AND INSTALL OLLAMA

Run: ollama --version

If not found:
  - Linux/WSL: curl -fsSL https://ollama.com/install.sh | sh
  - macOS: brew install ollama
  Then start it: ollama serve &
  Wait a few seconds for it to come up.

If Ollama is already installed, make sure it's running:
  Run: curl -s http://localhost:11434/api/tags
  If you get "connection refused", start it: ollama serve &
  Wait a few seconds and retry.

Pull the embedding model:
  Run: ollama pull nomic-embed-text

Quick sanity check — make sure embeddings actually work:
  Run: curl -s http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test"}' | head -c 100
  You should see JSON with an "embedding" key. If not, stop and tell me.

STEP 3 -- CLONE AND INSTALL CONTEXTMATE

Run these commands:
  git clone https://github.com/itscool2b/Cerno.git ~/ContextMate
  cd ~/ContextMate
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt

If git clone fails because ~/ContextMate already exists, just pull updates:
  cd ~/ContextMate && git pull

If pip install fails:
  pip install --upgrade pip
  Then rerun pip install -r requirements.txt

Verify the install:
  cd ~/ContextMate && source venv/bin/activate && python3 -c "from server import mcp; print('OK')"
  Must print "OK". If it fails with an ImportError about native libraries
  (libstdc++, libz, etc.), you're likely on NixOS or a minimal distro —
  tell me the exact error.

STEP 4 -- REGISTER THE MCP SERVER

First, get the absolute path:
  Run: CMPATH=$(cd ~/ContextMate && pwd) && echo $CMPATH

Then register it with Claude Code:
  Run: claude mcp add-json context-mate "{\"type\":\"stdio\",\"command\":\"$CMPATH/venv/bin/python3\",\"args\":[\"server.py\"],\"cwd\":\"$CMPATH\"}"

Note: the escaped quotes are required — this is a JSON string passed as
a shell argument. If you get a parse error, make sure the backslashes
are intact.

If it fails because context-mate already exists:
  Run: claude mcp remove context-mate
  Then rerun the add-json command above.

Verify:
  Run: claude mcp list
  "context-mate" must appear in the output.

STEP 5 -- CONFIGURE THE PROJECT

THIS STEP IS REQUIRED — it tells Claude how to use the tools.

Create a file called CLAUDE.md in the root of my current project directory
(the directory I opened Claude Code in, NOT ~/ContextMate). If CLAUDE.md
already exists, append to it. Write exactly this:

---START---
## Context Retrieval

This project uses the `context-mate` MCP server for semantic code search
with layered context (repo map, file signatures, dependencies, and
targeted chunks).

Rules:
- At the start of every session, call `index_directory` with the absolute
  path to this project root. This indexes all supported files so search
  and context tools work across the entire project.
- Use `read_file` instead of reading files directly. Pass the file path
  and a short reason describing what you're looking for. It returns only
  the relevant chunks with surrounding context, not the whole file.
- Use `search_codebase` with a natural language query to find code related
  to a concept or behavior. Prefer this over grep or glob for exploratory
  questions.
- Use `get_repo_map` to get a compact overview of the indexed codebase —
  file paths and function/class signatures. Useful for orientation or when
  you need to know what's available without reading everything.
- Prefer MCP tools over direct file access. Only fall back to direct reads
  when the MCP tools don't return what you need.
- Token budgets are adjustable: `read_file` defaults to 4,000 tokens and
  `search_codebase` defaults to 6,000. Pass a higher `token_budget` for
  complex queries that need more context.
- After a session with significant MCP usage, call `get_session_summary`
  to report how many targeted chunks were served and tokens saved.
---END---

After writing the file, read it back to confirm it looks right.

STEP 6 -- RESTART

Tell me: "Setup complete. Exit Claude Code fully and reopen it. Run /mcp
and confirm you see context-mate with 5 tools."
```

---

## What You Get

After setup, Claude Code has five new tools:

| Tool | What it does | Default budget |
|---|---|---|
| `index_directory(path)` | Index all supported files in a directory, skipping .git/node_modules/venv/etc | — |
| `read_file(path, reason)` | Index a file and return only the chunks relevant to your reason, with layered context | 4,000 tokens |
| `search_codebase(query)` | Search all indexed files for code matching a natural language query | 6,000 tokens |
| `get_repo_map(directory?)` | Return a compact map of the indexed codebase: file paths + function/class signatures | — |
| `get_session_summary()` | Show how many queries and chunks were served this session, plus tokens saved | — |

Claude will automatically use these instead of reading entire files, keeping
context focused and costs down.

---

## How It Works — 4-Layer Context System

When you call `search_codebase` or `read_file`, ContextMate doesn't just
return raw matching chunks. It assembles a layered response with four types
of context, each with its own token budget:

### Layer 1: Repo Map (15% of budget)

A compact overview of the entire indexed codebase — file paths and
function/class signatures. Gives Claude structural awareness of the project
without loading any code.

```
src/auth/oauth.py
  class OAuthProvider(BaseProvider)
    def authenticate(request: Request) -> Token
src/models/user.py
  class User(BaseModel)
    def has_permission(perm: str) -> bool
```

*Only included for `search_codebase` (repo-wide queries).*

### Layer 2: File Context (20% of budget)

For each file that contributed a matching chunk, includes the imports and
all function/class signatures from that file. This tells Claude what else
lives in the same file without loading all the code.

### Layer 3: Dependency Context (15% of budget)

For the top 5 matching chunks, resolves the call graph:
- **Calls** — signatures of functions this code calls
- **Called by** — signatures of functions that call this code

This gives Claude the dependency relationships around each match.

### Layer 4: Semantic Chunks (50% of budget)

The actual matching code, ranked by semantic similarity. These are the
tree-sitter-extracted functions, classes, and definitions that best match
your query.

### Budget Redistribution

Each layer uses only what it needs. Unused tokens flow to the next layer:

```
Chunks (50%) --> File Context (20%) --> Dependencies (15%) --> Repo Map (15%)
```

If chunks only use 40% of their budget, the remaining 10% flows to file
context, and so on. Nothing is wasted.

For `read_file`, the budget splits differently (no repo map):
chunks 55%, file context 25%, dependencies 20%.

---

## Architecture

```
  read_file / search_codebase / index_directory
                    |
                server.py              MCP tool definitions, session stats
                    |
          indexingpipeline.py          parse -> chunk -> embed -> store
           /        |        \
     chunker.py  ollama.py  chroma.py
     tree-sitter  embed via   ChromaDB
     AST parsing  nomic-embed  storage
           \        |        /
                context.py             4-layer context assembly + budgeting
                    |
                 graph.py              repo map + dependency resolution
                    |
              tokencount.py            token estimation + truncation
```

| Module | Role |
|---|---|
| `server.py` | MCP server entry point — defines the 5 tools and tracks session stats |
| `indexingpipeline.py` | Orchestrates the parse-chunk-embed-store pipeline with content hashing |
| `chunker.py` | Multi-language tree-sitter parser with nested extraction for 10 languages |
| `ollama.py` | Thin wrapper around Ollama's HTTP API (`nomic-embed-text`, 768 dimensions) |
| `chroma.py` | ChromaDB client — two collections: `contextmate` (chunks) and `contextmate_files` (metadata) |
| `context.py` | Assembles the 4-layer context response with token budgeting and redistribution |
| `graph.py` | Builds the repo map and resolves call/called-by dependency signatures |
| `tokencount.py` | Estimates tokens (~3.5 chars/token) and truncates text to fit budgets |
| `watcher.py` | Directory scanner — walks the file tree, skips junk directories, triggers indexing |

---

## Supported Languages

| Language | Extensions | Nested extraction |
|---|---|---|
| Python | `.py` | Methods inside classes |
| JavaScript | `.js` `.jsx` `.mjs` | Methods inside classes |
| TypeScript | `.ts` `.tsx` | Methods inside classes |
| Rust | `.rs` | Functions inside impl blocks |
| Go | `.go` | — |
| Java | `.java` | Methods + constructors inside classes |
| C | `.c` `.h` | — |
| C++ | `.cpp` `.cc` `.cxx` `.hpp` | Functions inside classes/namespaces |
| Ruby | `.rb` | Methods inside classes/modules |
| C# | `.cs` | Methods + constructors inside classes |

**Nested extraction** means methods inside classes are extracted as their own
individual chunks, so a query about a specific method won't pull the entire
class.

---

## Manual Setup

If you prefer to do it yourself or the prompt above doesn't work for your
environment.

### Prerequisites

| Dependency | Install |
|---|---|
| Python 3.11+ | `brew install python3` / `sudo apt install python3 python3-venv` |
| Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Claude Code | https://docs.anthropic.com/en/docs/claude-code |

Start Ollama and pull the model:

```
ollama serve &
ollama pull nomic-embed-text
```

### Install

```
git clone https://github.com/itscool2b/Cerno.git ~/ContextMate
cd ~/ContextMate
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Register

```
CMPATH=$(cd ~/ContextMate && pwd)
claude mcp add-json context-mate \
  "{\"type\":\"stdio\",\"command\":\"$CMPATH/venv/bin/python3\",\"args\":[\"server.py\"],\"cwd\":\"$CMPATH\"}"
```

Restart Claude Code. Run `/mcp` to confirm `context-mate` appears with 5 tools.

### Configure your project

Add the context retrieval rules to `CLAUDE.md` in your project root. See the
setup prompt above for the exact text.

---

## Manage

```bash
claude mcp list                          # see registered servers
claude mcp remove context-mate           # unregister
rm -rf ~/ContextMate/contextmate_db/     # wipe all indexed data
```

To re-index a project, call `index_directory` again — it only re-embeds
files that have changed (content hashing skips unchanged files).

---

## File Structure

```
ContextMate/
  server.py              MCP server entry point, 5 tool definitions, session stats
  context.py             4-layer context assembly with token budgeting
  graph.py               repo map generation + dependency resolution (calls/called-by)
  tokencount.py          token estimation (~3.5 chars/token) and truncation
  chunker.py             multi-language tree-sitter parser, AST to semantic chunks
  indexingpipeline.py    parse -> chunk -> embed -> store, with content hashing
  chroma.py              ChromaDB client, two collections (chunks + file metadata)
  ollama.py              Ollama embedding client (nomic-embed-text, 768 dims)
  watcher.py             directory scanner, skips junk dirs, triggers indexing
  requirements.txt       Python dependencies
  test_context_layers.py tests for the 4-layer context system
  contextmate_db/        persistent vector storage (gitignored)
```

---

## Troubleshooting

**Tools not showing in `/mcp`** — Run `claude mcp list` to confirm
registration. Restart Claude Code after registering. If the server crashes
silently, test manually:
`cd ~/ContextMate && source venv/bin/activate && python3 -c "from server import mcp; print('OK')"`

**"Connection refused"** — Ollama isn't running. Start it with
`ollama serve`. Confirm the model is pulled with `ollama list`.

**Empty search results** — Files must be indexed first. Call
`index_directory` on the project root to bulk-index, then `search_codebase`
will find results.

**"No module named 'mcp.types'"** — A file named `mcp.py` is shadowing the
`mcp` package. The server file is named `server.py` to avoid this. Don't
rename it.

**Embedding fails on large files** — This is handled automatically. Chunks
are individually embedded (not whole files), and each chunk is truncated to
8,192 tokens before embedding. Classes with nested methods are extracted as
separate chunks, so even large classes won't exceed the limit.

**Re-indexing** — Call `read_file` on the file again, or `index_directory`
on the project. If the file has changed, old chunks are deleted and the file
is re-indexed automatically. Unchanged files are skipped.

**Full reset** — `rm -rf ~/ContextMate/contextmate_db/`
