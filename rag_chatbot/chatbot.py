import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Union
from google import genai
# Fix import from relative to absolute
from rag_chatbot.retriever import JobRetriever
import json

# Load environment variables
load_dotenv()

# Initialize Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

class JobChatbot:
    def __init__(self, retriever: JobRetriever = None):
        """Initialize the chatbot with a retriever."""
        self.retriever = retriever or JobRetriever()
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model = "gemini-2.0-flash"
        self.history = []
    
    def reset_chat(self) -> None:
        """Reset the chat history."""
        self.history = []
    
    def format_context(self, contexts: List[Dict[str, Any]]) -> str:
        """Format retrieved contexts into a single string."""
        formatted_context = "RELEVANT JOB INFORMATION:\n\n"
        
        for i, ctx in enumerate(contexts, 1):
            metadata = ctx['metadata']
            formatted_context += f"JOB {i}:\n"
            formatted_context += f"Title: {metadata.get('job_title', 'N/A')}\n"
            formatted_context += f"Employer: {metadata.get('employer_name', 'N/A')}\n"
            formatted_context += f"Location: {metadata.get('job_location', 'N/A')}\n"
            formatted_context += f"Description: {ctx['text'][:1000]}...\n\n"
        
        return formatted_context
    
    def generate_response(self, user_query: str, job_type: str) -> Dict[str, Any]:
        """
        Generate a response to the user query using the RAG approach.
        
        Args:
            user_query: The user's question
            job_type: The job type to search for context
            
        Returns:
            A dictionary containing the response and metadata
        """
        try:
            # Retrieve relevant contexts
            contexts = self.retriever.retrieve_relevant_context(user_query, job_type)
            
            if not contexts:
                return {
                    "response": "I don't have enough information about this job type. Please try another job category or load job data first.",
                    "sources": [],
                    "error": None
                }
            
            # Format context
            formatted_context = self.format_context(contexts)
            
            # Add the current interaction to history
            self.history.append({"role": "user", "content": user_query})
            
            # Create the prompt with context and history
            prompt = f"""You are an AI career advisor specializing in helping people understand job descriptions, requirements, and career paths.
            
Use the following job information to answer the user's question. Only use this information and don't make up facts.
If you don't know the answer based on the provided context, say so honestly.

{formatted_context}

User query: {user_query}

Provide a detailed, helpful response focusing specifically on what's asked. If multiple jobs are mentioned in the context, compare them when relevant to the query.
"""
            
            # Generate response with Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            # Add the response to history
            self.history.append({"role": "assistant", "content": response.text})
            
            # Extract source information
            sources = []
            for ctx in contexts:
                sources.append({
                    "job_id": ctx['metadata'].get('job_id'),
                    "job_title": ctx['metadata'].get('job_title'),
                    "employer": ctx['metadata'].get('employer_name'),
                    "relevance_score": ctx['score']
                })
            
            return {
                "response": response.text,
                "sources": sources,
                "error": None
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "sources": [],
                "error": str(e)
            }
