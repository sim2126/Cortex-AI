from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add the new routers
from api.ingestion_router import router as ingestion_router
from api.ontology_router import router as ontology_router
from api.knowledge_router import router as knowledge_router

# Add the root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from core.agent_logic import app as cortex_ai_agent
from api.streaming_models import QueryRequest
from api.streaming_logic import stream_agent_response

app = FastAPI(
    title="Cortex AI API - Final",
    description="API for the Cortex AI Agentic RAG system with multi-source ingestion.",
    version="4.0.0"
)

# --- THIS IS THE CORRECTED CORS CONFIGURATION ---
# We are explicitly allowing the frontend's address.
origins = [
    "http://localhost",
    "http://localhost:3000", # The address of your Next.js UI
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, DELETE etc.)
    allow_headers=["*"], # Allows all headers
)

# --- Include all the Routers ---
app.include_router(ontology_router)
app.include_router(ingestion_router)
app.include_router(knowledge_router)

@app.post("/query")
async def query_agent(request: QueryRequest):
    """
    Receives a question and streams the agent's reasoning and final answer.
    """
    print(f"Received streaming query: {request.question}")
    return stream_agent_response(request.question)

@app.get("/")
def read_root():
    return {"message": "Cortex AI API v4 with PDF Ingestion is running."}

