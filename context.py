import json
from tokencount import estimate_tokens, truncate_to_budget
from chroma import get_file_metadata
from graph import build_repo_map, get_dependency_context

# Budget allocation ratios
BUDGET_REPO_SCOPE = {"chunks": 0.50, "file_context": 0.20, "dependencies": 0.15, "repo_map": 0.15}
BUDGET_FILE_SCOPE = {"chunks": 0.55, "file_context": 0.25, "dependencies": 0.20}


def assemble_context(query, raw_results, budget, scope="repo"):
    """Assemble a layered context response within a token budget.

    Args:
        query: the original query string
        raw_results: list of {"text": ..., "metadata": {...}} dicts from ChromaDB
        budget: total token budget
        scope: "repo" for search_codebase, "file" for read_file
    """
    if scope == "file":
        ratios = BUDGET_FILE_SCOPE
    else:
        ratios = BUDGET_REPO_SCOPE

    chunk_budget = int(budget * ratios["chunks"])
    file_ctx_budget = int(budget * ratios["file_context"])
    dep_budget = int(budget * ratios["dependencies"])
    map_budget = int(budget * ratios.get("repo_map", 0))

    # Layer 4: Full chunks (most important, fill first in relevance order)
    chunks_out = []
    chunks_tokens = 0
    for r in raw_results:
        text = r["text"]
        t = estimate_tokens(text)
        if chunks_tokens + t > chunk_budget:
            break
        chunks_out.append(r)
        chunks_tokens += t

    unused = chunk_budget - chunks_tokens

    # Layer 2: File context (imports + signatures for each result's file)
    file_context = {}
    file_ctx_tokens = 0
    file_ctx_budget += unused  # redistribute unused chunk budget
    unused = 0
    seen_paths = set()

    for r in chunks_out:
        path = r["metadata"].get("path", "")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)

        meta = get_file_metadata(path)
        if not meta:
            continue

        imports = meta.get("imports", "[]")
        if isinstance(imports, str):
            imports = json.loads(imports)

        defs_raw = meta.get("definitions", "[]")
        if isinstance(defs_raw, str):
            defs = json.loads(defs_raw)
        else:
            defs = defs_raw

        sigs = [d.get("signature", "") for d in defs if d.get("signature")]

        entry_text = "\n".join(imports + sigs)
        t = estimate_tokens(entry_text)
        if file_ctx_tokens + t > file_ctx_budget:
            continue
        file_context[path] = {"imports": imports, "signatures": sigs}
        file_ctx_tokens += t

    unused = file_ctx_budget - file_ctx_tokens

    # Layer 3: Dependency context (call/called-by signatures for top chunks)
    dependency_context = {}
    dep_tokens = 0
    dep_budget += unused
    unused = 0

    for r in chunks_out[:5]:  # top 5 chunks only
        name = r["metadata"].get("name", "")
        if not name:
            continue
        deps = get_dependency_context(r["metadata"])
        if not deps["calls"] and not deps["called_by"]:
            continue

        entry_text = "\n".join(deps["calls"] + deps["called_by"])
        t = estimate_tokens(entry_text)
        if dep_tokens + t > dep_budget:
            continue
        dependency_context[name] = deps
        dep_tokens += t

    unused = dep_budget - dep_tokens

    # Layer 1: Repo map (compact overview, only for repo scope)
    repo_map_text = ""
    if scope == "repo" and map_budget > 0:
        map_budget += unused
        raw_map = build_repo_map()
        repo_map_text = truncate_to_budget(raw_map, map_budget)

    total_tokens = chunks_tokens + file_ctx_tokens + dep_tokens + estimate_tokens(repo_map_text)

    # Estimate tokens saved vs returning just raw chunk text
    raw_tokens = sum(estimate_tokens(r["text"]) for r in raw_results)

    return {
        "query": query,
        "repo_map": repo_map_text,
        "file_context": file_context,
        "dependency_context": dependency_context,
        "chunks": [{"text": r["text"], "metadata": r["metadata"]} for r in chunks_out],
        "stats": {
            "chunks_included": len(chunks_out),
            "tokens_used": total_tokens,
            "tokens_saved": max(0, raw_tokens - total_tokens),
        },
    }
