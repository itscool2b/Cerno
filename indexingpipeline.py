from ollama import Ai
from chunker import parse, chunk
from chroma import upsert_chunk, delete_file, is_indexed
import hashlib


def index(path):
    if is_indexed(path):
        delete_file(path)

    tree = parse(path)

    with open(path, "rb") as f:
        source = f.read()

    chunks = chunk(tree, source)

    for i, c in enumerate(chunks):
        text = c["text"]
        embedding = Ai(text).embed()
        chunk_id = hashlib.sha256(f"{path}:{i}:{c['start_line']}".encode()).hexdigest()
        metadata = {
            "path": path,
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "type": c["type"],
        }
        upsert_chunk(chunk_id, embedding, text, metadata)
