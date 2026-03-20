import chromadb

client = chromadb.PersistentClient(path="./contextmate_db")
collection = client.get_or_create_collection(name="contextmate")
file_collection = client.get_or_create_collection(name="contextmate_files")

def upsert_chunk(chunk_id, embedding, text, metadata):
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata]
    )

def query_chunks(query_vector, path=None, n_results=5):
    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": n_results,
        "include": ["documents", "metadatas"],
    }
    if path is not None:
        kwargs["where"] = {"path": path}
    return collection.query(**kwargs)

def get_file_hash(path):
    """Return the stored content hash for a file, or None if not indexed."""
    existing = collection.get(where={"path": path}, limit=1)
    if existing["ids"]:
        return existing["metadatas"][0].get("content_hash")
    return None

def delete_file(path):
    collection.delete(where={"path": path})
    # Also clean up file metadata
    try:
        file_collection.delete(ids=[path])
    except Exception:
        pass

def upsert_file_metadata(file_path, metadata_json, content_hash):
    """Store file-level metadata (imports, definitions) keyed by path."""
    file_collection.upsert(
        ids=[file_path],
        documents=[metadata_json],
        metadatas=[{"path": file_path, "content_hash": content_hash}],
    )

def get_file_metadata(file_path):
    """Retrieve one file's metadata, or None if not stored."""
    import json
    result = file_collection.get(ids=[file_path])
    if not result["ids"]:
        return None
    doc = result["documents"][0]
    return json.loads(doc)

def get_all_file_metadata():
    """Retrieve all file metadata entries (for repo map)."""
    import json
    result = file_collection.get()
    if not result["ids"]:
        return []
    return [json.loads(doc) for doc in result["documents"]]
