import os
from chunker import get_language_config
from indexingpipeline import index

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "build", "dist", ".next", "target"}


def scan(path):
    results = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = os.path.join(root, f)
            if get_language_config(fp):
                try:
                    results.append(index(fp))
                except Exception as e:
                    results.append({"status": "error", "message": f"Failed to index {fp}: {e}"})
    return results
