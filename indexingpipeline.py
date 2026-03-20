import hashlib
import json
import os

from ollama import Ai
from chunker import parse, chunk, get_language_config, extract_file_metadata
from chroma import upsert_chunk, upsert_file_metadata, delete_file, get_file_hash
from tokencount import truncate_to_budget

EMBED_TOKEN_LIMIT = 8192


def index(path):
    """Index a file into ChromaDB. Skips if file content hasn't changed.
    Returns a status dict with 'status' and 'message' keys."""

    if not os.path.isfile(path):
        return {"status": "error", "message": f"File not found: {path}"}

    if get_language_config(path) is None:
        return {"status": "error", "message": f"Unsupported file type: {os.path.splitext(path)[1]}"}

    # Hash file contents to detect changes
    with open(path, "rb") as f:
        content = f.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Skip re-indexing if file hasn't changed
    stored_hash = get_file_hash(path)
    if stored_hash == content_hash:
        return {"status": "skipped", "message": "File unchanged, using cached index."}

    # Clear old chunks before re-indexing
    if stored_hash is not None:
        delete_file(path)

    tree, source, config = parse(path)
    chunks = chunk(tree, source, config)

    if not chunks:
        return {"status": "warning", "message": "No semantic chunks found in file."}

    # Store file-level metadata for context layers
    file_meta = extract_file_metadata(path)
    upsert_file_metadata(path, json.dumps(file_meta), content_hash)

    # Embed each chunk and store in ChromaDB
    embedded = 0
    for c in chunks:
        try:
            embed_text = truncate_to_budget(c["text"], EMBED_TOKEN_LIMIT)
            embedding = Ai(embed_text).embed()
            chunk_id = hashlib.sha256(f"{path}:{c['start_line']}:{c['end_line']}".encode()).hexdigest()
            metadata = {
                "path": path,
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "type": c["type"],
                "content_hash": content_hash,
                "name": c.get("name", ""),
                "signature": c.get("signature", ""),
                "calls": json.dumps(c.get("calls", [])),
                "docstring": c.get("docstring", ""),
            }
            upsert_chunk(chunk_id, embedding, c["text"], metadata)
            embedded += 1
        except Exception as e:
            print(f"Warning: failed to embed chunk {c.get('name', '?')} in {path}: {e}")

    if embedded == 0:
        return {"status": "warning", "message": f"File has {len(chunks)} chunks but none could be embedded."}
    return {"status": "indexed", "message": f"Indexed {embedded}/{len(chunks)} chunks."}
