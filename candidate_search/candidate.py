import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Check if Tavily is installed, if not provide instructions
try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError("The Tavily package is required. Install it using: pip install tavily-python")

# Create the router
router = APIRouter()

# --- Configuration ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
MAX_RESULTS = 20

# Initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# Models
class CandidateSearchRequest(BaseModel):
    job_type: str
    location: str
    max_results: Optional[int] = MAX_RESULTS

class CandidateResponse(BaseModel):
    profile_url: str
    title: str
    snippet: str
    job_type: str
    location: str
    search_query: str
    found_at: str

class CandidateSearchResponse(BaseModel):
    candidates: List[CandidateResponse]
    count: int
    search_query: str
    job_type: str
    location: str

def search_with_tavily(query, max_results=MAX_RESULTS):
    """
    Search using Tavily API with increased result count
    """
    print(f"🔍 Searching with Tavily: {query} (requesting up to {max_results} results)")
    try:
        # Add max_results parameter to get more search results
        response = tavily_client.search(query, max_results=max_results)
        results = response.get("results", [])
        print(f"   Found {len(results)} results")
        return results
    except Exception as e:
        print(f"🚨 Error searching with Tavily: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching with Tavily: {str(e)}")

@router.post("/search", response_model=CandidateSearchResponse)
async def find_candidates(request: CandidateSearchRequest):
    """
    Find LinkedIn profiles of candidates based on job type and location.
    """
    job_type = request.job_type
    location = request.location
    max_results = request.max_results

    # Build the search query using the user input
    search_query = f'site:linkedin.com/in OR site:linkedin.com/pub intitle:{job_type} AND ({location}) AND intext:Open to Work'
    
    # Step 1: Search with Tavily
    try:
        search_results = search_with_tavily(search_query, max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if not search_results:
        return CandidateSearchResponse(
            candidates=[],
            count=0,
            search_query=search_query,
            job_type=job_type,
            location=location
        )
    
    # Step 2: Process the LinkedIn URLs
    linkedin_candidates = []
    
    for result in search_results:
        url = result.get("url")
        if not url or "linkedin.com" not in url:
            continue
            
        # Extract candidate info from the search result
        candidate = CandidateResponse(
            profile_url=url,
            title=result.get("title", "No title available"),
            snippet=result.get("content", "No content available"),
            search_query=search_query,
            job_type=job_type,
            location=location,
            found_at=datetime.now().isoformat()
        )
        
        linkedin_candidates.append(candidate)
    
    # Return the response
    return CandidateSearchResponse(
        candidates=linkedin_candidates,
        count=len(linkedin_candidates),
        search_query=search_query,
        job_type=job_type,
        location=location
    )

@router.get("/search", response_model=CandidateSearchResponse)
async def find_candidates_get(
    job_type: str = Query(..., description="Job type or skill (e.g., 'SQL Developer')"),
    location: str = Query(..., description="Location (e.g., 'India', 'Bangalore')"),
    max_results: int = Query(MAX_RESULTS, description="Maximum number of results to return")
):
    """GET endpoint version of the candidate search"""
    request = CandidateSearchRequest(
        job_type=job_type,
        location=location,
        max_results=max_results
    )
    return await find_candidates(request)
