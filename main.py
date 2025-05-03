from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import importlib.util

# Add code to handle directories with hyphens
hyphen_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "Job-search"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidate_search")
]

for hyphen_dir in hyphen_dirs:
    if hyphen_dir not in sys.path:
        sys.path.insert(0, hyphen_dir)
    
# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Helper function to load modules directly from file paths
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Use try-except for importing the modules
try:
    # Import Job-search modules
    from Job_search import job_search, job_details, job_salary, resume_parser
    
    # Import rag_chatbot
    from rag_chatbot import api as rag_chatbot
    
    # Import candidate directly from file path
    candidate = load_module_from_path(
        "candidate", 
        os.path.join(current_dir, "candidate-search", "candidate.py")
    )
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
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
app.include_router(rag_chatbot.router, prefix="/api/chatbot", tags=["AI Chatbot"])

# Include the candidate search router
app.include_router(candidate.router, prefix="/api/candidates", tags=["Candidate Search"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Search API. Use /docs to view the API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
