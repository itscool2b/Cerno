import chromadb

client = chromadb.PersistentClient(path="./contextmate_db")
collection = client.get_or_create_collection(name="contextmate")

def is_indexed(path):
    existing = collection.get(where={"path": path}, limit=1)
    return len(existing["ids"]) > 0

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

def delete_file(path):
    collection.delete(where={"path": path})
