from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
import PyPDF2
import docx
from google import genai
import tempfile
import json

load_dotenv()

router = APIRouter()

# Initialize Google Gemini client
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

# Define the resume schema
RESUME_SCHEMA = {
    "basic_info": {
        "name": "string",
        "email": "string",
        "phone": "string",
        "location": "string"
    },
    "skills": ["string"],
    "technical_skills": ["string"],
    "soft_skills": ["string"],
    "experience": [{
        "job_title": "string",
        "company": "string",
        "duration": "string",
        "description": "string"
    }],
    "education": [{
        "degree": "string",
        "institution": "string",
        "year": "string"
    }],
    "certifications": ["string"],
    "years_of_experience": "number",
    "recommended_job_roles": ["string"] # Added field for job role recommendations
}

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from DOCX: {str(e)}")

def parse_resume_with_gemini(text: str) -> Dict[str, Any]:
    """Parse resume text using Google Gemini."""
    try:
        # Set up the prompt for Gemini
        prompt = f"""
        You are a professional resume parser and career advisor. Given the following resume text, extract the information and format it according to the schema provided.
        
        Resume text:
        {text}
        
        For the recommended_job_roles field, analyze the skills, experience, and education from the resume to suggest 5-7 specific job roles that would be a good match for this candidate. Be specific with job titles rather than general fields.
        
        Return ONLY a JSON object matching this schema (do not include explanations, just the JSON):
        {json.dumps(RESUME_SCHEMA, indent=2)}
        
        Ensure your response is strictly formatted as valid JSON with no other text.
        """

        response = client.models.generate_content(model="gemini-2.0-flash",contents=prompt)
        
        # Extract JSON from the response
        response_text = response.text
        
        # Clean up response to ensure it's valid JSON
        # Remove markdown code block markers if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
            if response_text.endswith("```"):
                response_text = response_text[:-3]
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
            if response_text.endswith("```"):
                response_text = response_text[:-3]
        
        parsed_data = json.loads(response_text.strip())
        return parsed_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume with Gemini: {str(e)}")

@router.post("/resume/parse", response_model=Dict[str, Any])
async def parse_resume(file: UploadFile = File(...)):
    """API endpoint to parse a resume file."""
    # Check file extension
    if not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name
    
    try:
        # Extract text from file
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(temp_file_path)
        else:  # .docx
            text = extract_text_from_docx(temp_file_path)
        
        # Parse resume with Gemini
        parsed_data = parse_resume_with_gemini(text)
        
        return parsed_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
