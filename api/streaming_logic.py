import json
import asyncio
from fastapi.responses import StreamingResponse

# Add the root directory to the Python path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.agent_logic import app as cortex_ai_agent

async def stream_agent_response_logic(question: str):
    """
    Runs the agent and streams back the thought process and final answer.
    """
    async for event in cortex_ai_agent.astream(
        {"question": question}
    ):
        last_node = list(event.keys())[-1]
        last_state = event[last_node]

        if 'streaming_thought' in last_state and last_state['streaming_thought']:
            data = {"type": "thought", "content": last_state['streaming_thought']}
            yield f"data: {json.dumps(data)}\n\n"
        
        if 'answer' in last_state and last_state['answer']:
            data = {"type": "answer", "content": last_state['answer']}
            yield f"data: {json.dumps(data)}\n\n"
        
        await asyncio.sleep(0.1)

def stream_agent_response(question: str):
    return StreamingResponse(
        stream_agent_response_logic(question),
        media_type="text/event-stream"
    )
