from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add code to handle Job-search directory with a hyphen
hyphen_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Job-search")
if hyphen_dir not in sys.path:
    sys.path.insert(0, hyphen_dir)
    
# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Use try-except for importing the modules
try:
    from Job_search import job_search, job_details, job_salary, resume_parser
    from rag_chatbot import api as rag_chatbot
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Create the FastAPI application
app = FastAPI(title="Job Search API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
app.include_router(job_search.router, prefix="/api", tags=["Job Search"])
app.include_router(job_details.router, prefix="/api", tags=["Job Details"])
app.include_router(job_salary.router, prefix="/api", tags=["Job Salary"])
app.include_router(resume_parser.router, prefix="/api", tags=["Resume Parser"])

# Include the rag_chatbot router
app.include_router(rag_chatbot.router, prefix="/api/chatbot", tags=["AI Chatbot"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Search API. Use /docs to view the API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
