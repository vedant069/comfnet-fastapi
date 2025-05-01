from fastapi import APIRouter, Query
import http.client
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

@router.get("/estimated-salary")
async def get_estimated_salary(
    job_title: str = Query(..., description="Job title"),
    location: str = Query(..., description="Location"),
    location_type: str = Query("ANY", description="Location type"),
    years_of_experience: str = Query("ALL", description="Years of experience")
):
    """Get estimated salary for a job title in a specific location."""
    conn = http.client.HTTPSConnection(os.getenv("RAPIDAPI_HOST"))
    
    headers = {
        'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),
        'x-rapidapi-host': os.getenv("RAPIDAPI_HOST")
    }
    
    # URL encode parameters
    import urllib.parse
    job_title_encoded = urllib.parse.quote(job_title)
    location_encoded = urllib.parse.quote(location)
    
    endpoint = f"/estimated-salary?job_title={job_title_encoded}&location={location_encoded}&location_type={location_type}&years_of_experience={years_of_experience}"
    
    conn.request("GET", endpoint, headers=headers)
    
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))

@router.get("/company-job-salary")
async def get_company_job_salary(
    company: str = Query(..., description="Company name"),
    job_title: str = Query(..., description="Job title"),
    location_type: str = Query("ANY", description="Location type"),
    years_of_experience: str = Query("ALL", description="Years of experience")
):
    """Get salary information for a specific job title at a specific company."""
    conn = http.client.HTTPSConnection(os.getenv("RAPIDAPI_HOST"))
    
    headers = {
        'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),
        'x-rapidapi-host': os.getenv("RAPIDAPI_HOST")
    }
    
    # URL encode parameters
    import urllib.parse
    company_encoded = urllib.parse.quote(company)
    job_title_encoded = urllib.parse.quote(job_title)
    
    endpoint = f"/company-job-salary?company={company_encoded}&job_title={job_title_encoded}&location_type={location_type}&years_of_experience={years_of_experience}"
    
    conn.request("GET", endpoint, headers=headers)
    
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))
