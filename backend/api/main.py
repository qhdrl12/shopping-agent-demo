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
                
                # Use astream_events for detailed streaming including LLM tokens
                final_response = ""
                workflow_result = None
                is_streaming_response = False
                current_node = None
                
                print(f"Starting workflow for: {request.message}")
                
                async for event in unified_workflow.workflow.astream_events(workflow_input, config=config, version="v2"):
                    event_type = event.get("event")
                    event_name = event.get("name", "")
                    event_data = event.get("data", {})
                    
                    # print(f"Event: {event_type}, Name: {event_name}, Data keys: {list(event_data.keys()) if isinstance(event_data, dict) else 'not dict'}")
                    
                    # Log potential errors
                    if event_type == "on_chain_error":
                        error_info = event_data.get("error", "Unknown error")
                        print(f"Chain error in {event_name}: {error_info}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'Chain error in {event_name}: {str(error_info)}'}, ensure_ascii=False)}\n\n"
                    
                    # Handle step completion
                    if event_type == "on_chain_end" and event_name in LLM_NODES:
                        if current_node == event_name:
                            current_node = None  # Reset current node after completion
                        yield f"data: {json.dumps({
                            'type': 'step_complete',
                            'session_id': session_id,
                            'completed_step': event_name,
                            'status': 'completed'
                        })}\n\n"
                    
                    # Handle search products completion - send search metadata
                    elif event_type == "on_chain_end" and event_name == "search_products":
                        search_metadata = event_data.get("output", {}).get("search_metadata")
                        if search_metadata:
                            yield f"data: {json.dumps({
                                'type': 'search_metadata',
                                'session_id': session_id,
                                'metadata': search_metadata,
                                'status': 'info'
                            }, ensure_ascii=False)}\n\n"
                    
                    # Handle workflow step updates
                    elif event_type == "on_chain_start" and event_name in LLM_NODES:
                        current_node = event_name  # Track current node
                        yield f"data: {json.dumps({
                            'type': 'step',
                            'session_id': session_id,
                            'current_step': event_name,
                            'is_llm_node': True,
                            'status': 'processing'
                        })}\n\n"
                    
                    # Handle non-LLM workflow steps
                    elif event_type == "on_chain_start" and event_name not in LLM_NODES and "workflow" not in event_name.lower():
                        yield f"data: {json.dumps({
                            'type': 'step',
                            'session_id': session_id,
                            'current_step': event_name,
                            'is_llm_node': False,
                            'status': 'processing'
                        })}\n\n"
                    
                    # Handle streaming tokens from LLM - for any response generation (final response or general query)
                    elif event_type == "on_chat_model_stream" and current_node in ["generate_final_response", "handle_general_query"]:
                        if not is_streaming_response:
                            is_streaming_response = True
                            # Clear any system messages when streaming starts
                            print(f"Starting token streaming for {current_node}")
                        
                        chunk_content = event_data.get("chunk", {})
                        if hasattr(chunk_content, 'content') and chunk_content.content:
                            try:
                                final_response += chunk_content.content
                                token_data = {
                                    'type': 'token',
                                    'session_id': session_id,
                                    'content': chunk_content.content,
                                    'status': 'streaming'
                                }
                                yield f"data: {json.dumps(token_data, ensure_ascii=False)}\n\n"
                            except Exception as e:
                                print(f"Error in token streaming: {e}")
                                yield f"data: {json.dumps({'type': 'error', 'error': f'Token streaming error: {str(e)}'})}\n\n"
                    
                    # Handle workflow completion
                    elif event_type == "on_chain_end" and "workflow" in event_name.lower():
                        workflow_result = event_data.get("output", {})
                
                # Handle completion
                suggested_questions = []
                if workflow_result:
                    suggested_questions = workflow_result.get('suggested_questions', [])
                
                # If we streamed tokens, send completion; otherwise fallback to full response
                try:
                    if is_streaming_response and final_response:
                        print(f"Completing streaming response. Total length: {len(final_response)}")
                        completion_data = {
                            'type': 'complete',
                            'session_id': session_id,
                            'current_step': 'completed',
                            'response': final_response,
                            'suggested_questions': suggested_questions,
                            'status': 'completed'
                        }
                        yield f"data: {json.dumps(completion_data, ensure_ascii=False)}\n\n"
                    elif workflow_result and workflow_result.get('final_response'):
                        # Fallback for non-streaming case
                        final_response = workflow_result.get('final_response', '')
                        print(f"Fallback to full response: {len(final_response)} chars")
                        fallback_data = {
                            'type': 'token', 
                            'session_id': session_id,
                            'content': final_response,
                            'suggested_questions': suggested_questions,
                            'status': 'streaming'
                        }
                        yield f"data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n"
                    else:
                        final_response = "죄송합니다. 응답을 생성할 수 없습니다."
                        error_data = {
                            'type': 'complete',
                            'session_id': session_id,
                            'current_step': 'completed', 
                            'response': final_response,
                            'suggested_questions': suggested_questions,
                            'status': 'completed'
                        }
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                except Exception as e:
                    print(f"Error in completion handling: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Completion error: {str(e)}'}, ensure_ascii=False)}\n\n"
                
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