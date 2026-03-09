from fastmcp import FastMCP
from ollama import Ai
from chroma import query_chunks
from indexingpipeline import index

mcp = FastMCP(
    name="context-mate",
    instructions="this is the mcp which fetches only relevant context for the codebase making ai decisions less sloppy and saves money. nice",
)

session_stats = {"queries": 0, "chunks_returned": 0}


@mcp.tool
def get_session_summary():
    """This tool is to give an overview of how much money you have saved using this mcp server."""
    return {
        "queries": session_stats["queries"],
        "chunks_returned": session_stats["chunks_returned"],
        "message": f"Served {session_stats['chunks_returned']} targeted chunks across {session_stats['queries']} queries instead of dumping entire files.",
    }


@mcp.tool
def read_file(path: str, reason: str):
    """This tool is for parsing specific files of relevant contents instead of random slop that isnt needed for the job or context as a whole."""
    index(path)
    query_embedding = Ai(reason).embed()
    results = query_chunks(query_embedding, path)
    session_stats["queries"] += 1
    session_stats["chunks_returned"] += len(results["documents"][0])
    return {
        "path": path,
        "reason": reason,
        "chunks": [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ],
    }


@mcp.tool
def search_codebase(query: str):
    """This is a tool that will search the code base for relevant code from relevant files based on a single query."""
    query_embedding = Ai(query).embed()
    results = query_chunks(query_embedding, path=None, n_results=10)
    session_stats["queries"] += 1
    session_stats["chunks_returned"] += len(results["documents"][0])
    return {
        "query": query,
        "results": [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ],
    }


if __name__ == "__main__":
    mcp.run()
