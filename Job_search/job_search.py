from fastapi import APIRouter, Query
import http.client
import json
import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# API Keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

@router.get("/job-search")
async def search_jobs(
    query: str = Query(..., description="Search query, e.g., 'developer jobs in chicago'"),
    page: int = Query(1, description="Page number"),
    num_pages: int = Query(1, description="Number of pages to retrieve"),
    country: str = Query("us", description="Country code"),
    date_posted: str = Query("all", description="Date posted filter")
):
    """Search for jobs based on query parameters."""
    # Get the result using the helper function that avoids FastAPI parameter annotation issues
    result = await search_jobs_direct(query, page, num_pages, country, date_posted)
    return result

# Create a separate function that doesn't rely on FastAPI Query parameters
async def search_jobs_direct(query: str, page: int = 1, num_pages: int = 1, 
                            country: str = "us", date_posted: str = "all"):
    """Direct function to search jobs without FastAPI Query objects"""
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': RAPIDAPI_HOST
    }
    
    # URL encode the query
    query_encoded = urllib.parse.quote(query)
    
    # Construct the endpoint with properly escaped parameters
    endpoint = f"/search?query={query_encoded}&page={page}&num_pages={num_pages}&country={country}&date_posted={date_posted}"
    
    conn.request("GET", endpoint, headers=headers)
    
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))
