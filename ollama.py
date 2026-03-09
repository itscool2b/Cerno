import requests

class Ai:

    def __init__(self, query, url="http://localhost:11434/api/embeddings"):
        self.query = query
        self.url = url

    def embed(self):
        response = requests.post(self.url, json={"model": "nomic-embed-text", "prompt": self.query})
        return response.json()["embedding"]
