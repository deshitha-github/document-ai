from RAG.vectorizer import search_similar

class IndexRetriever:
    @staticmethod
    def legal_knowledge_base(query: str, k: int = 3, threshold: float = 0.4) -> str:
        """
        Retrieve the most relevant text chunks from Weaviate vector store.
        If nothing passes the similarity threshold, return a 'not found' message.
        """
        hits = search_similar(query, k)
        if not hits:
            return "I couldn't find relevant information about that in the uploaded documents."

        # Filter by similarity / distance if available
        filtered = [h["text"] for h in hits if h.get("score", 1.0) <= threshold]
        if not filtered:
            return "I couldn't find relevant information about that in the uploaded documents."

        # Merge relevant chunks
        return "\n\n---\n\n".join(filtered)
