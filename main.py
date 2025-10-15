from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import json
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.agent_logic import app as cortex_ai_agent

class QueryRequest(BaseModel):
    question: str

app = FastAPI(
    title="Cortex AI API - Enhanced",
    description="API for the Cortex AI Agentic RAG system with multi-step reasoning.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_agent_response(question: str):
    """
    Runs the agent and streams back the thought process and final answer.
    """
    async for event in cortex_ai_agent.astream(
        {"question": question}
    ):
        # The event contains the full state of the graph after each step
        # We look for the last executed node to get the most recent thought
        last_node = list(event.keys())[-1]
        last_state = event[last_node]

        if 'streaming_thought' in last_state and last_state['streaming_thought']:
            data = {"type": "thought", "content": last_state['streaming_thought']}
            yield f"data: {json.dumps(data)}\n\n"
        
        if 'answer' in last_state and last_state['answer']:
            data = {"type": "answer", "content": last_state['answer']}
            yield f"data: {json.dumps(data)}\n\n"
        
        await asyncio.sleep(0.1)

@app.post("/query")
async def query_agent(request: QueryRequest):
    """
    Receives a question and streams the agent's reasoning and final answer.
    """
    print(f"Received streaming query: {request.question}")
    return StreamingResponse(
        stream_agent_response(request.question),
        media_type="text/event-stream"
    )

@app.get("/")
def read_root():
    return {"message": "Cortex AI API v2 is running."}