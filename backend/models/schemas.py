import operator
from typing import Annotated, List, Optional, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Legacy state model - kept for backward compatibility"""
    messages: Annotated[List[BaseMessage], operator.add]
    search_query: Optional[str]
    search_results: Optional[List[str]]
    scraped_data: Optional[List[Dict[str, Any]]]
    analysis_result: Optional[str]
    final_response: Optional[str]
    current_step: str
    query_analysis: Optional[Dict[str, Any]]
    primary_keywords: Optional[List[str]]
    secondary_keywords: Optional[List[str]]
    search_queries: Optional[List[str]]
    query_type: Optional[str]
    search_attempts: Optional[int]
    failed_extractions: Optional[List[str]]
    analysis_text: Optional[str]
    relevance_validation: Optional[Dict[str, Any]]
    product_insights: Optional[List[Dict[str, Any]]]