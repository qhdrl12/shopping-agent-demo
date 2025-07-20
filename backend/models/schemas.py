import operator

from typing import Annotated, List, Optional, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    search_query: Optional[str] = None
    search_results: Optional[List[str]] = None
    scraped_data: Optional[List[Dict[str, Any]]] = None
    analysis_result: Optional[str] = None
    final_response: Optional[str] = None
    current_step: str = "start"
    # New fields for enhanced workflow
    query_analysis: Optional[Dict[str, Any]] = None
    primary_keywords: Optional[List[str]] = None
    secondary_keywords: Optional[List[str]] = None
    search_queries: Optional[List[str]] = None
    query_type: Optional[str] = None
    search_attempts: Optional[int] = None
    failed_extractions: Optional[List[str]] = None
    analysis_text: Optional[str] = None
    relevance_validation: Optional[Dict[str, Any]] = None
    product_insights: Optional[List[Dict[str, Any]]] = None

# class ChatRequest(BaseModel):
#     message: str
#     session_id: Optional[str] = None

# class ChatResponse(BaseModel):
#     response: str
#     session_id: str
#     messages: List[BaseMessage]
#     status: str = "completed"