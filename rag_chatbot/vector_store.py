import os
import psycopg2
import numpy as np
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import json
import datetime

# Load environment variables
load_dotenv()

class NeonDBVectorStore:
    """Vector store implementation using NeonDB and pgvector"""
    
    def __init__(self):
        """Initialize the NeonDB vector store"""
        # Use individual connection parameters instead of connection string
        self.conn_params = {
            "host": os.getenv("NEONDB_HOST"),
            "dbname": os.getenv("NEONDB_NAME"),
            "user": os.getenv("NEONDB_USER"),
            "password": os.getenv("NEONDB_PASSWORD"),
            "port": os.getenv("NEONDB_PORT", "5432"),
            "sslmode": "require"
        }
        
        # Ensure pgvector extension is created
        self._initialize_db()
    
    def _get_connection(self):
        """Get a connection to the NeonDB database"""
        return psycopg2.connect(**self.conn_params)
    
    def _initialize_db(self):
        """Initialize the database with necessary tables and extensions"""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            # Create pgvector extension if it doesn't exist
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create tables if they don't exist
            cur.execute(""" 
            CREATE TABLE IF NOT EXISTS job_categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            cur.execute(""" 
            CREATE TABLE IF NOT EXISTS job_documents (
                id SERIAL PRIMARY KEY,
                job_id TEXT NOT NULL,
                category_id INTEGER REFERENCES job_categories(id) ON DELETE CASCADE,
                job_title TEXT NOT NULL,
                employer_name TEXT,
                job_location TEXT,
                job_description TEXT,
                embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (job_id, category_id)
            );
            """)
            
            # Create an index for faster similarity search
            cur.execute(""" 
            CREATE INDEX IF NOT EXISTS job_documents_embedding_idx 
            ON job_documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error initializing database: {str(e)}")
            raise
        finally:
            conn.close()
    
    def add_job_category(self, category_name: str) -> int:
        """
        Add a job category to the database or get its ID if it already exists
        
        Args:
            category_name: The name of the job category
            
        Returns:
            The ID of the category
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            # First try to fetch existing category
            cur.execute("SELECT id FROM job_categories WHERE name = %s", (category_name,))
            result = cur.fetchone()
            
            if result:
                return result[0]
            
            # If not found, insert new category
            cur.execute(
                "INSERT INTO job_categories (name) VALUES (%s) RETURNING id",
                (category_name,)
            )
            category_id = cur.fetchone()[0]
            conn.commit()
            return category_id
        except Exception as e:
            conn.rollback()
            print(f"Error adding job category: {str(e)}")
            raise
        finally:
            conn.close()
    
    def store_job_embeddings(self, category_name: str, jobs: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Store job embeddings in the database
        
        Args:
            category_name: The name of the job category
            jobs: List of job data dictionaries
            embeddings: List of embedding vectors corresponding to the jobs
        """
        if len(jobs) != len(embeddings):
            raise ValueError("Number of jobs and embeddings must match")
        
        category_id = self.add_job_category(category_name)
        
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            for job, embedding in zip(jobs, embeddings):
                # Extract job fields
                job_id = job.get('job_id')
                job_title = job.get('job_title', '')
                employer_name = job.get('employer_name', '')
                job_location = job.get('job_location', '')
                job_description = job.get('job_description', '')
                
                # Create metadata with other job fields
                metadata = {k: v for k, v in job.items() if k not in ('job_id', 'job_title', 'employer_name', 'job_location', 'job_description')}
                
                # Insert into database with proper casting to vector type
                cur.execute(""" 
                INSERT INTO job_documents 
                    (job_id, category_id, job_title, employer_name, job_location, job_description, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)
                ON CONFLICT (job_id, category_id) 
                DO UPDATE SET 
                    job_title = EXCLUDED.job_title,
                    employer_name = EXCLUDED.employer_name,
                    job_location = EXCLUDED.job_location,
                    job_description = EXCLUDED.job_description,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """, (
                    job_id, 
                    category_id, 
                    job_title, 
                    employer_name, 
                    job_location, 
                    job_description, 
                    embedding, 
                    json.dumps(metadata)
                ))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error storing job embeddings: {str(e)}")
            raise
        finally:
            conn.close()
    
    def search_similar_jobs(self, category_name: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for jobs similar to the query embedding
        
        Args:
            category_name: The name of the job category to search in
            query_embedding: The embedding vector of the query
            top_k: The number of top results to return
            
        Returns:
            List of similar jobs with their metadata and similarity scores
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            # Get category ID
            cur.execute("SELECT id FROM job_categories WHERE name = %s", (category_name,))
            result = cur.fetchone()
            
            if not result:
                return []
            
            category_id = result[0]
            
            # Search for similar jobs with proper vector casting
            cur.execute(""" 
            SELECT 
                job_id, 
                job_title, 
                employer_name, 
                job_location, 
                job_description,
                metadata,
                1 - (embedding <=> %s::vector) as similarity
            FROM job_documents
            WHERE category_id = %s
            ORDER BY similarity DESC
            LIMIT %s
            """, (query_embedding, category_id, top_k))
            
            results = []
            for row in cur.fetchall():
                job_id, job_title, employer_name, job_location, job_description, metadata_json, similarity = row
                
                # Parse metadata
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                # Create result object
                result = {
                    'job_id': job_id,
                    'job_title': job_title,
                    'employer_name': employer_name,
                    'job_location': job_location,
                    'job_description': job_description,
                    'metadata': metadata,
                    'similarity': float(similarity)
                }
                
                results.append(result)
            
            return results
        except Exception as e:
            print(f"Error searching similar jobs: {str(e)}")
            return []
        finally:
            conn.close()
    
    def delete_job_category(self, category_name: str) -> bool:
        """
        Delete a job category and all associated jobs
        
        Args:
            category_name: The name of the job category to delete
            
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            # Get category ID
            cur.execute("SELECT id FROM job_categories WHERE name = %s", (category_name,))
            result = cur.fetchone()
            
            if not result:
                return False
            
            category_id = result[0]
            
            # Delete all jobs in this category first
            cur.execute("DELETE FROM job_documents WHERE category_id = %s", (category_id,))
            
            # Delete the category
            cur.execute("DELETE FROM job_categories WHERE id = %s", (category_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting job category: {str(e)}")
            return False
        finally:
            conn.close()
    
    def list_job_categories(self) -> List[str]:
        """
        List all job categories in the database
        
        Returns:
            List of category names
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT name FROM job_categories ORDER BY name")
            
            return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"Error listing job categories: {str(e)}")
            return []
        finally:
            conn.close()
