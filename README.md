# ContextMate

**Semantic code search for Claude Code.** Instead of dumping entire files into
context, ContextMate indexes your codebase into meaningful chunks and returns
only what matters. Local embeddings. No API keys. No cloud.

Supports **Python, JavaScript, TypeScript, Rust, Go, Java, C, C++, Ruby, and C#**.

```
tree-sitter (parse) --> Ollama (embed) --> ChromaDB (store/query)
```

---

## One-Command Setup

Paste this prompt into Claude Code. It handles everything.

```
Set up ContextMate, a local MCP server that gives you semantic code search.
Follow these steps in order. Run each command, check the output, and only
move on if it succeeded. If something fails, diagnose and fix it before
continuing.

STEP 1 -- CHECK PYTHON

Run: python3 --version

If the command is not found or the version is below 3.11:
  - macOS: run "brew install python3" (install Homebrew first if needed
    with /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)")
  - Linux: run "sudo apt install python3 python3-venv" (or the equivalent
    for the distro)
  - WSL: same as Linux

Run again to confirm python3 >= 3.11 is available. Also confirm python3-venv
is available by running: python3 -m venv --help
If that fails on Linux, run: sudo apt install python3-venv

STEP 2 -- CHECK AND INSTALL OLLAMA

Run: ollama --version

If the command is not found:
  - Linux/WSL: run "curl -fsSL https://ollama.com/install.sh | sh"
  - macOS: run "brew install ollama"
  After installing, start it: ollama serve &
  Wait 3 seconds for it to start.

If ollama is installed, check if it is running:
  Run: curl -s http://localhost:11434/api/tags
  If that fails with "connection refused", start it: ollama serve &
  Wait 3 seconds, then retry the curl.

Pull the embedding model:
  Run: ollama pull nomic-embed-text

Verify embeddings work:
  Run: curl -s http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test"}' | head -c 100
  You should see JSON with an "embedding" key. If not, stop and tell me.

STEP 3 -- CLONE AND INSTALL CONTEXTMATE

Run:
  git clone https://github.com/itscool2b/Cerno.git ~/ContextMate
  cd ~/ContextMate
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt

If git clone fails because ~/ContextMate already exists:
  Run: cd ~/ContextMate && git pull

If pip install fails, try: pip install --upgrade pip && then rerun the
pip install line.

Verify:
  Run: cd ~/ContextMate && source venv/bin/activate && python3 -c "from server import mcp; print('OK')"
  Must print "OK". If it fails with an ImportError about native libraries
  (libstdc++, libz, etc.), you are likely on NixOS or a minimal distro.
  Tell me the exact error.

STEP 4 -- REGISTER THE MCP SERVER

Get the absolute path:
  Run: CMPATH=$(cd ~/ContextMate && pwd) && echo $CMPATH

Register:
  Run: claude mcp add-json context-mate "{\"type\":\"stdio\",\"command\":\"$CMPATH/venv/bin/python3\",\"args\":[\"server.py\"],\"cwd\":\"$CMPATH\"}"

If that fails because context-mate already exists:
  Run: claude mcp remove context-mate
  Then rerun the add-json command.

Verify registration:
  Run: claude mcp list
  "context-mate" must appear in the output.

STEP 5 -- CONFIGURE THE PROJECT

THIS STEP IS MANDATORY. DO NOT SKIP IT.

Create a file called CLAUDE.md in the root of my current project directory
(the directory I opened Claude Code in, NOT ~/ContextMate). If CLAUDE.md
already exists, append to it. Write exactly this content:

---START---
## Context Retrieval

This project uses the `context-mate` MCP server for semantic code search.

Rules:
- At the start of every session, call `index_directory` with the absolute
  path to this project root. This indexes all supported files so
  `search_codebase` works across the entire project.
- Use `read_file` instead of reading files directly. Pass the file path
  and a short reason. It returns only the relevant chunks, not the whole
  file.
- Use `search_codebase` with a natural language query to find code related
  to a concept or behavior. Do not grep or glob unless the MCP results
  are insufficient.
- Prefer MCP tools over direct file access. Only fall back to direct reads
  when the MCP tools do not return what you need.
- After a session with significant MCP usage, call `get_session_summary`
  to report how many targeted chunks were served.
---END---

After writing the file, verify it exists by reading it back.

STEP 6 -- RESTART

Tell me: "Setup complete. Exit Claude Code fully and reopen it. Run /mcp
and confirm you see context-mate with 4 tools."
```

---

## What You Get

After setup, Claude Code has four new tools:

| Tool | What it does |
|---|---|
| `index_directory(path)` | Indexes all supported files in a directory, skipping .git/node_modules/venv/etc |
| `read_file(path, reason)` | Indexes a file and returns only the chunks relevant to your reason |
| `search_codebase(query)` | Searches all indexed files for code matching a natural language query |
| `get_session_summary()` | Shows how many queries and chunks were served this session |

Claude will automatically use these instead of reading entire files, keeping
context focused and costs down.

---

## Manual Setup

If you prefer to do it yourself or the prompt above does not work for your
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

Restart Claude Code. Run `/mcp` to confirm `context-mate` appears.

### Configure your project

Add the context retrieval rules to `CLAUDE.md` in your project root. See the
prompt above for the exact text.

### Manage

```
claude mcp list              # see registered servers
claude mcp remove context-mate  # unregister
rm -rf ~/ContextMate/contextmate_db/  # wipe indexed data
```

---

## How It Works

```
  read_file("api.py", "auth logic")
       |
       v
  +-----------+     +--------+     +----------+
  | tree-sitter| --> | Ollama | --> | ChromaDB |
  | parse AST  |    | embed  |     | store    |
  +-----------+     +--------+     +----------+
                                        |
                          query with     |
                          same model     |
                                        v
                                 top matching chunks
                                 returned to Claude
```

**Indexing** -- When `read_file` is called, tree-sitter parses the file into
an AST using the correct grammar for the file's language. Top-level functions,
classes, interfaces, structs, and other definitions are extracted as chunks.
Each chunk is embedded with Ollama (`nomic-embed-text`, 768 dimensions) and
stored in ChromaDB with metadata (path, line range, type, content hash).

**Smart re-indexing** -- File contents are hashed on each call. If the file
hasn't changed since it was last indexed, the embedding step is skipped
entirely, saving time and compute.

**Querying** -- The query string is embedded with the same model. ChromaDB
runs vector similarity search and returns the top matching chunks.
`read_file` scopes to one file. `search_codebase` searches everything indexed.

**Storage** -- ChromaDB persists to `./contextmate_db/` on disk. Data survives
restarts. Changed files are re-indexed automatically on the next `read_file`
or `index_directory` call.

---

## Supported Languages

| Language | Extensions |
|---|---|
| Python | `.py` |
| JavaScript | `.js` `.jsx` `.mjs` |
| TypeScript | `.ts` `.tsx` |
| Rust | `.rs` |
| Go | `.go` |
| Java | `.java` |
| C | `.c` `.h` |
| C++ | `.cpp` `.cc` `.cxx` `.hpp` |
| Ruby | `.rb` |
| C# | `.cs` |

---

## File Structure

```
ContextMate/
  server.py            MCP server entry point, tool definitions
  watcher.py           directory scanner, skips junk dirs
  chroma.py            ChromaDB client, storage and query
  chunker.py           multi-language tree-sitter parser, AST to chunks
  indexingpipeline.py  parse -> chunk -> embed -> store
  ollama.py            Ollama embedding client
  requirements.txt     Python dependencies
  contextmate_db/      persistent vector storage (gitignored)
```

---

## Troubleshooting

**Tools not showing in `/mcp`** -- Run `claude mcp list` to confirm
registration. Restart Claude Code after registering. If the server crashes
silently, test manually: `cd ~/ContextMate && source venv/bin/activate &&
python3 -c "from server import mcp; print('OK')"`

**"Connection refused"** -- Ollama is not running. Start it with
`ollama serve`. Confirm the model is pulled with `ollama list`.

**Empty search results** -- Files must be indexed first. Call
`index_directory` on the project root to bulk-index, then `search_codebase`
will find results.

**"No module named 'mcp.types'"** -- A file named `mcp.py` is shadowing the
`mcp` package. The server file is named `server.py` to avoid this. Do not
rename it.

**Re-indexing** -- Call `read_file` on the file again. If the file has changed,
old chunks are deleted and the file is re-indexed automatically.

**Full reset** -- `rm -rf ~/ContextMate/contextmate_db/`
