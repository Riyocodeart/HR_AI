import faiss
import numpy as np

class FAISSIndex:

    def __init__(self, dimension=384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.candidate_ids = []

    def add(self, embeddings, candidate_ids):
        embeddings = np.asarray(embeddings, dtype=np.float32)
        self.index.add(embeddings)
        self.candidate_ids.extend(candidate_ids)
        
    def search(self, embedding, k=5):
        embedding = np.asarray([embedding], dtype=np.float32)
        scores, indices = self.index.search(embedding, k)
        results = []

        for score, idx in zip(scores[0], indices[0]):

            results.append({
                "candidate_id": self.candidate_ids[idx],
                "score": float(score)
            })

        return results
    
    def save(self, path):
        faiss.write_index(self.index, path)

    def load(self, path):
        self.index = faiss.read_index(path)
