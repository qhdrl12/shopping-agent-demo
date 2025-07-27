import operator
from typing import Annotated, List, Optional, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from datetime import datetime


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


# Kakao Pay Payment Models
class PaymentReadyRequest(BaseModel):
    """카카오페이 결제 준비 요청 모델"""
    product_name: str
    product_url: str
    quantity: int = 1
    total_amount: int
    vat_amount: Optional[int] = None
    tax_free_amount: int = 0


class PaymentReadyResponse(BaseModel):
    """카카오페이 결제 준비 응답 모델"""
    tid: str
    next_redirect_app_url: Optional[str] = None
    next_redirect_mobile_url: Optional[str] = None
    next_redirect_pc_url: Optional[str] = None
    android_app_scheme: Optional[str] = None
    ios_app_scheme: Optional[str] = None
    created_at: datetime


class PaymentApproveRequest(BaseModel):
    """카카오페이 결제 승인 요청 모델"""
    tid: str
    pg_token: str


class PaymentApproveResponse(BaseModel):
    """카카오페이 결제 승인 응답 모델"""
    aid: str
    tid: str
    cid: str
    sid: Optional[str] = None
    partner_order_id: str
    partner_user_id: str
    payment_method_type: str
    amount: Dict[str, int]
    item_name: str
    item_code: Optional[str] = None
    quantity: int
    created_at: datetime
    approved_at: datetime


class PaymentErrorResponse(Exception):
    """카카오페이 결제 에러 예외 클래스"""
    def __init__(self, error_code: str, error_message: str, extras: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.error_message = error_message
        self.extras = extras
        super().__init__(error_message)
    
    def dict(self):
        """FastAPI 호환을 위한 dict 메서드"""
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "extras": self.extras
        }