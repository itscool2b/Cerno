from fastmcp import FastMCP
from ollama import Ai
from chroma import query_chunks
from indexingpipeline import index
from watcher import scan
from context import assemble_context
from graph import build_repo_map

mcp = FastMCP(
    name="context-mate",
    instructions="Semantic code search MCP server. Indexes code into meaningful chunks and returns only what's relevant. Supports Python, JavaScript, TypeScript, Rust, Go, Java, C, C++, Ruby, and C#.",
)

session_stats = {"queries": 0, "chunks_returned": 0, "tokens_saved": 0}


@mcp.tool
def get_session_summary():
    """Returns stats on how many queries and chunks were served this session."""
    return {
        "queries": session_stats["queries"],
        "chunks_returned": session_stats["chunks_returned"],
        "tokens_saved": session_stats["tokens_saved"],
        "message": f"Served {session_stats['chunks_returned']} targeted chunks across {session_stats['queries']} queries. Estimated {session_stats['tokens_saved']} tokens saved via context layers.",
    }


@mcp.tool
def read_file(path: str, reason: str, token_budget: int = 4000):
    """Index a file and return only the chunks relevant to the given reason, with layered context.
    Supports: .py .js .jsx .mjs .ts .tsx .rs .go .java .c .h .cpp .cc .cxx .hpp .rb .cs"""
    result = index(path)
    if result["status"] == "error":
        return {"error": result["message"]}

    query_embedding = Ai(reason).embed()
    results = query_chunks(query_embedding, path)
    session_stats["queries"] += 1

    raw_results = [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

    response = assemble_context(reason, raw_results, token_budget, scope="file")
    response["path"] = path
    response["index_status"] = result["message"]

    session_stats["chunks_returned"] += response["stats"]["chunks_included"]
    session_stats["tokens_saved"] += response["stats"]["tokens_saved"]
    return response


@mcp.tool
def search_codebase(query: str, token_budget: int = 6000):
    """Search all indexed files for code matching a natural language query. Returns layered context."""
    query_embedding = Ai(query).embed()
    results = query_chunks(query_embedding, path=None, n_results=10)
    session_stats["queries"] += 1

    raw_results = [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

    response = assemble_context(query, raw_results, token_budget, scope="repo")

    session_stats["chunks_returned"] += response["stats"]["chunks_included"]
    session_stats["tokens_saved"] += response["stats"]["tokens_saved"]
    return response


@mcp.tool
def get_repo_map(directory: str = None):
    """Return a compact map of the indexed codebase: file paths + function/class signatures."""
    return {"repo_map": build_repo_map(directory)}


@mcp.tool
def index_directory(path: str):
    """Index all supported files in a directory."""
    results = scan(path)
    return {"indexed": sum(1 for r in results if r["status"] == "indexed"), "total": len(results)}


if __name__ == "__main__":
    mcp.run()
