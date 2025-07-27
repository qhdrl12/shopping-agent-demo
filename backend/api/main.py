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
from ..services.kakao_pay_service import kakao_pay_service
from ..models.schemas import (
    PaymentReadyRequest, 
    PaymentReadyResponse,
    PaymentApproveRequest, 
    PaymentApproveResponse,
    PaymentErrorResponse
)

# Load environment variables
load_dotenv()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    suggested_questions: list[str] = []
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
    'generate_final_response': 'AI가 최종 답변을 생성하고 있습니다...',
    'generate_suggested_questions': 'AI가 추천 질문을 생성하고 있습니다...'
}

@app.get("/")
async def root():
    return {"message": "Musinsa Shopping Agent API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle non-streaming chat requests"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Prepare workflow input
        workflow_input = {
            "messages": [HumanMessage(content=request.message)]
        }
        
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 15
        }
        
        # Execute workflow
        result = await unified_workflow.workflow.ainvoke(workflow_input, config=config)
        
        # Extract response and suggested questions
        final_response = result.get('final_response', '응답을 생성할 수 없습니다.')
        suggested_questions = result.get('suggested_questions', [])
        
        # Store session
        sessions[session_id] = final_response
        
        return ChatResponse(
            response=final_response,
            session_id=session_id,
            suggested_questions=suggested_questions,
            status="completed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

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
                captured_questions = []  # Store questions when generated
                
                print(f"Starting workflow for: {request.message}")
                
                async for event in unified_workflow.workflow.astream_events(workflow_input, config=config, version="v2"):
                    event_type = event.get("event")
                    event_name = event.get("name", "")
                    event_data = event.get("data", {})
                    
                    # Log potential errors
                    if event_type == "on_chain_error":
                        error_info = event_data.get("error", "Unknown error")
                        print(f"Chain error in {event_name}: {error_info}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'Chain error in {event_name}: {str(error_info)}'}, ensure_ascii=False)}\n\n"
                    
                    # Handle step completion
                    if event_type == "on_chain_end" and event_name in LLM_NODES:
                        if current_node == event_name:
                            current_node = None  # Reset current node after completion
                        
                        # Special handling for question generation completion
                        if event_name == "generate_suggested_questions":
                            output = event_data.get("output", {})
                            questions = output.get("suggested_questions", [])
                            # Capture questions for later use
                            captured_questions = questions if questions else []
                        
                        yield f"data: {json.dumps({
                            'type': 'step_complete',
                            'session_id': session_id,
                            'completed_step': event_name,
                            'status': 'completed'
                        })}\n\n"
                    
                    # Handle search products completion - send search metadata and step completion
                    elif event_type == "on_chain_end" and event_name == "search_products":
                        # Send step completion event first
                        yield f"data: {json.dumps({
                            'type': 'step_complete',
                            'session_id': session_id,
                            'completed_step': event_name,
                            'status': 'completed'
                        })}\n\n"
                        
                        # Then send search metadata if available
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
                    
                    # Handle non-LLM workflow steps (including search_products)
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
                
                # Handle completion - use captured questions first, then workflow result
                suggested_questions = captured_questions if captured_questions else workflow_result.get('suggested_questions', []) if workflow_result else []
                
                # Determine final response
                if is_streaming_response and final_response:
                    response_text = final_response
                elif workflow_result and workflow_result.get('final_response'):
                    response_text = workflow_result.get('final_response', '')
                else:
                    response_text = "죄송합니다. 응답을 생성할 수 없습니다."
                
                # Send completion response
                try:
                    completion_data = {
                        'type': 'complete',
                        'session_id': session_id,
                        'current_step': 'completed',
                        'response': response_text,
                        'suggested_questions': suggested_questions,
                        'status': 'completed'
                    }
                    yield f"data: {json.dumps(completion_data, ensure_ascii=False)}\n\n"
                except Exception as e:
                    print(f"Error in completion handling: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Completion error: {str(e)}'}, ensure_ascii=False)}\n\n"
                
                # Store session response
                sessions[session_id] = response_text
                
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

# Kakao Pay Payment Endpoints

@app.post("/payment/ready", response_model=PaymentReadyResponse)
async def payment_ready(payment_request: PaymentReadyRequest):
    """카카오페이 결제 준비 API"""
    try:
        response = await kakao_pay_service.prepare_payment(payment_request)
        return response
    except PaymentErrorResponse as e:
        raise HTTPException(status_code=400, detail=e.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결제 준비 중 오류가 발생했습니다: {str(e)}")

@app.post("/payment/approve", response_model=PaymentApproveResponse)
async def payment_approve(approve_request: PaymentApproveRequest):
    """카카오페이 결제 승인 API"""
    try:
        response = await kakao_pay_service.approve_payment(approve_request)
        return response
    except PaymentErrorResponse as e:
        raise HTTPException(status_code=400, detail=e.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결제 승인 중 오류가 발생했습니다: {str(e)}")

@app.get("/payment/session/{tid}")
async def get_payment_session(tid: str):
    """결제 세션 정보 조회"""
    payment_session = kakao_pay_service.get_payment_session(tid)
    if not payment_session:
        raise HTTPException(status_code=404, detail="결제 세션을 찾을 수 없습니다")
    return payment_session

@app.delete("/payment/session/{tid}")
async def clear_payment_session(tid: str):
    """결제 세션 정보 삭제"""
    success = kakao_pay_service.clear_payment_session(tid)
    if not success:
        raise HTTPException(status_code=404, detail="결제 세션을 찾을 수 없습니다")
    return {"message": "결제 세션이 삭제되었습니다"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)