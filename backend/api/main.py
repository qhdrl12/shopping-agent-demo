import asyncio
import json
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

from ..workflow.unified_workflow import unified_workflow

# Load environment variables
load_dotenv()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str = "completed"

app = FastAPI(title="Musinsa Shopping Agent API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage (in production, use Redis or database)
sessions: Dict[str, str] = {}

# Constants
LLM_NODES = {
    'analyze_query': 'AI가 질문을 분석하고 있습니다...',
    'handle_general_query': 'AI가 답변을 생성하고 있습니다...',
    'optimize_search_query': 'AI가 검색어를 최적화하고 있습니다...',
    'generate_final_response': 'AI가 최종 답변을 생성하고 있습니다...'
}

@app.get("/")
async def root():
    return {"message": "Musinsa Shopping Agent API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Handle streaming chat requests with token-level streaming"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        print(f"session_id: {session_id}")
        async def generate():
            try:
                final_response = ""            
                # Prepare workflow input with user message
                workflow_input = {
                    "messages": [HumanMessage(content=request.message)]
                }

                config = {
                    "configurable": {"thread_id": session_id},
                    "recursion_limit": 15
                }
                
                # Use original astream approach with token simulation
                final_response = ""
                workflow_result = None
                
                
                # First run the workflow and get the result
                print(f"Starting workflow for: {request.message}")
                
                async for chunk in unified_workflow.workflow.astream(workflow_input, config=config, stream_mode="values"):
                    print(f"Workflow chunk: {chunk}")
                    
                    # Send step update
                    current_step = None
                    if isinstance(chunk, dict) and chunk.get('current_step'):
                        current_step = chunk['current_step']
                    elif hasattr(chunk, 'current_step'):
                        current_step = chunk.current_step
                    
                    if current_step:
                        # Check if this is an LLM node
                        is_llm_node = current_step in LLM_NODES
                        
                        yield f"data: {json.dumps({
                            'type': 'step',
                            'session_id': session_id,
                            'current_step': current_step,
                            'is_llm_node': is_llm_node,
                            'status': 'processing'
                        })}\n\n"
                        
                        # Send additional LLM processing notification for LLM nodes
                        if is_llm_node:
                            
                            yield f"data: {json.dumps({
                                'type': 'llm_processing',
                                'session_id': session_id,
                                'node_name': current_step,
                                'message': LLM_NODES.get(current_step, 'AI 처리 중...'),
                                'status': 'llm_running'
                            })}\n\n"
                    
                    workflow_result = chunk
                
                # Extract final response
                if workflow_result:
                    if isinstance(workflow_result, dict):
                        final_response = workflow_result.get('final_response', '')
                    else:
                        final_response = getattr(workflow_result, 'final_response', '')
                
                print(f"Final response to stream: {final_response}")
                
                # Stream the final response token by token
                if final_response:
                    yield f"data: {json.dumps({
                            'type': 'token',
                            'session_id': session_id,
                            'content': final_response,
                            'status': 'streaming'
                        })}\n\n"
                else:
                    final_response = "죄송합니다. 응답을 생성할 수 없습니다."
                    yield f"data: {json.dumps({
                        'type': 'complete',
                        'session_id': session_id,
                        'current_step': 'completed',
                        'response': final_response,
                        'status': 'completed'
                    })}\n\n"
                
                # Store session response
                sessions[session_id] = final_response
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    response = sessions[session_id]
    return {
        "session_id": session_id,
        "response": response,
        "status": "completed"
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "sessions": list(sessions.keys()),
        "count": len(sessions)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)