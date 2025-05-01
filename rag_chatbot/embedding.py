import os
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
import datetime
from .vector_store import NeonDBVectorStore

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service with the specified model."""
        self.model = SentenceTransformer(model_name)
        self.vector_store = NeonDBVectorStore()
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embeddings for a single text."""
        return self.model.encode(text)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts)
    
    def create_job_embeddings(self, job_data: List[Dict[str, Any]], job_type: str) -> None:
        """
        Create embeddings for job descriptions and save them in NeonDB.
        
        Args:
            job_data: List of job objects containing job descriptions
            job_type: The type/category of jobs for organizing embeddings
        """
        # Clean the job type name for storage
        safe_job_type = "".join(c if c.isalnum() else "_" for c in job_type)
        
        # Extract texts for embedding
        job_texts = []
        valid_jobs = []
        
        for job in job_data:
            # Extract the job description
            description = job.get('job_description', '')
            title = job.get('job_title', '')
            
            if not description or not title:
                continue
                
            # Combine title and description for better embedding context
            combined_text = f"{title}\n\n{description}"
            job_texts.append(combined_text)
            valid_jobs.append(job)
        
        if not job_texts:
            print(f"No valid job texts found for {job_type}")
            return
            
        # Generate embeddings
        print(f"Generating embeddings for {len(job_texts)} jobs...")
        embeddings = self.embed_texts(job_texts)
        embeddings_list = [embedding.tolist() for embedding in embeddings]
        
        # Store in NeonDB
        print(f"Storing embeddings in NeonDB for job type: {safe_job_type}")
        self.vector_store.store_job_embeddings(safe_job_type, valid_jobs, embeddings_list)
        print(f"Successfully stored {len(valid_jobs)} job embeddings for {safe_job_type}")
    
    def delete_job_embeddings(self, job_type: str) -> bool:
        """Delete embeddings for a specific job type."""
        return self.vector_store.delete_job_category(job_type)
    
    def list_job_types(self) -> List[str]:
        """List all job types with embeddings."""
        return self.vector_store.list_job_categories()
