import requests


class Ai:

    def __init__(self, query, url="http://localhost:11434/api/embeddings"):
        self.query = query
        self.url = url

    def embed(self):
        response = requests.post(
            self.url,
            json={"model": "nomic-embed-text", "prompt": self.query},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]
