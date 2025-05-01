from typing import List, Dict, Any
import numpy as np
# Fix import from relative to absolute
from rag_chatbot.embedding import EmbeddingService

class JobRetriever:
    def __init__(self, embedding_service: EmbeddingService = None):
        """Initialize the retriever with an embedding service."""
        self.embedding_service = embedding_service or EmbeddingService()
    
    def get_job_types(self) -> List[str]:
        """Get all available job types."""
        return self.embedding_service.list_job_types()
    
    def retrieve_relevant_context(self, query: str, job_type: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant job contexts for a query.
        
        Args:
            query: The user query
            job_type: The job type to search in
            top_k: Number of top results to return
            
        Returns:
            List of relevant contexts with metadata
        """
        try:
            # Embed the query
            query_embedding = self.embedding_service.embed_text(query)
            
            # Search for similar documents in NeonDB
            search_results = self.embedding_service.vector_store.search_similar_jobs(
                job_type, 
                query_embedding.tolist(), 
                top_k
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    'text': result['job_description'],
                    'metadata': {
                        'job_id': result['job_id'],
                        'job_title': result['job_title'],
                        'employer_name': result['employer_name'],
                        'job_location': result['job_location']
                    },
                    'score': result['similarity']
                })
            
            return results
        except Exception as e:
            print(f"Error retrieving context: {str(e)}")
            return []
