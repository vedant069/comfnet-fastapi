from fastapi import APIRouter, Query
import http.client
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

@router.get("/job-details")
async def get_job_details(
    job_id: str = Query(..., description="Job ID to retrieve details for"),
    country: str = Query("us", description="Country code")
):
    """Get detailed information about a specific job."""
    conn = http.client.HTTPSConnection(os.getenv("RAPIDAPI_HOST"))
    
    headers = {
        'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),
        'x-rapidapi-host': os.getenv("RAPIDAPI_HOST")
    }
    
    # URL encode the job_id
    import urllib.parse
    job_id_encoded = urllib.parse.quote(job_id)
    
    endpoint = f"/job-details?job_id={job_id_encoded}&country={country}"
    
    conn.request("GET", endpoint, headers=headers)
    
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))
