from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from pydantic import BaseModel
import os
import time
import datetime
import asyncio
import json

# Change relative imports to absolute imports
from rag_chatbot.embedding import EmbeddingService
from rag_chatbot.retriever import JobRetriever  
from rag_chatbot.chatbot import JobChatbot
from Job_search.job_search import search_jobs_direct

router = APIRouter()

# Initialize services
embedding_service = EmbeddingService()
retriever = JobRetriever(embedding_service)
chatbot = JobChatbot(retriever)

# Models
class ChatMessage(BaseModel):
    query: str
    job_type: str

class SearchJobsRequest(BaseModel):
    job_type: str
    location: str = "Remote"
    num_results: int = 10

# Endpoints
@router.get("/job-types")
async def get_job_types():
    """Get all available job types with embeddings."""
    try:
        job_types = retriever.get_job_types()
        return {"job_types": job_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search-and-index-jobs")
async def search_and_index_jobs(request: SearchJobsRequest, background_tasks: BackgroundTasks):
    """Search for jobs and index them for RAG."""
    try:
        # Clean job type for filename
        safe_job_type = "".join(c if c.isalnum() else "_" for c in request.job_type)
        
        # Background task to fetch and index jobs
        def fetch_and_index():
            try:
                # Create a new event loop for the background task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Format the location properly for the search 
                location = request.location.strip().replace(" ", "+")
                
                # Format the query string properly for the search API
                search_query = f"{request.job_type.strip()} jobs in {location}"
                
                # Use the direct function instead of the FastAPI route handler
                response = loop.run_until_complete(
                    search_jobs_direct(
                        query=search_query, 
                        page=1, 
                        num_pages=1
                    )
                )
                
                if response.get("status") != "OK":
                    print(f"Error fetching jobs: {response}")
                    return
                
                jobs = response.get("data", [])
                
                if not jobs:
                    print("No jobs found")
                    return
                
                # Truncate to requested number
                jobs = jobs[:request.num_results]
                
                # Process job data to only include necessary fields
                processed_jobs = []
                for job in jobs:
                    processed_job = {
                        "job_id": job.get("job_id"),
                        "job_title": job.get("job_title"),
                        "employer_name": job.get("employer_name"),
                        "job_location": job.get("job_location"),
                        "job_description": job.get("job_description")
                    }
                    processed_jobs.append(processed_job)
                
                # Index jobs in vector DB
                embedding_service.create_job_embeddings(processed_jobs, safe_job_type)
                print(f"Successfully indexed {len(processed_jobs)} jobs for {safe_job_type}")
            
            except Exception as e:
                print(f"Error in background task: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Add task to background
        background_tasks.add_task(fetch_and_index)
        
        return {
            "message": f"Started indexing jobs for '{request.job_type}'. This may take a few minutes.",
            "job_type": safe_job_type
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(message: ChatMessage):
    """Chat with the AI about specific job types."""
    try:
        response = chatbot.generate_response(message.query, message.job_type)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/job-type/{job_type}")
async def delete_job_type(job_type: str):
    """Delete a job type and its embeddings."""
    try:
        success = embedding_service.delete_job_embeddings(job_type)
        if success:
            return {"message": f"Successfully deleted embeddings for {job_type}"}
        else:
            raise HTTPException(status_code=404, detail=f"Job type {job_type} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-chat")
async def reset_chat():
    """Reset the chat history."""
    try:
        chatbot.reset_chat()
        return {"message": "Chat history reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
