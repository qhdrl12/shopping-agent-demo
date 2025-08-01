"""
Query analysis and handling nodes with streaming support
"""

import json
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..utils.model import load_chat_model

from ..prompts.system_prompts import (
    QUERY_ANALYSIS_PROMPT,
    GENERAL_QUERY_PROMPT,
    SEARCH_QUERY_OPTIMIZATION_PROMPT
)

BRAND_CODES = {
    "살로몬": "salomon",
    "마크모크": "macmoc",
    "마크 모크": "macmoc", 
    "크록스": "cros",
    "아틀리에": "nain",
    "아틀리에 나인": "nain",
    "시눈": "sinoon",
    "파라부트": "paraboot",
    "킨": "keen",
    "나이키": "nike"
}

def format_brand_codes_for_prompt() -> str:
    """브랜드 코드를 시스템 프롬프트용 표 형태로 포맷팅"""
    brand_table = """브랜드명 매핑 규칙:
사용자가 한글 브랜드명을 언급하면 다음 표에 따라 영문 코드로 변환하세요.

| 사용자 입력 | 검색 코드 |
|------------|-----------|"""
    
    for korean_name, brand_code in BRAND_CODES.items():
        brand_table += f"\n| {korean_name} | {brand_code} |"
    
    brand_table += "\n\n사용법: brand=[영문코드] 파라미터로 추가\n예시: '살로몬 운동화' → brand=SALOMON"
    
    return brand_table

class QueryAnalysisOutput(BaseModel):
    """Structured output for query analysis"""
    query_type: Literal["search_required", "general"] = Field(
        description="Type of query: search_required for product searches, general for other queries"
    )

class QueryOptimizationOutput(BaseModel):
    """
    Musinsa 검색 최적화를 위한 구조화된 출력 클래스
    
    사용자의 자연어 질문을 Musinsa 검색에 최적화된 형태로 분리:
    - 핵심 검색어: 상품명/카테고리 등 기본 검색어
    - 검색 파라미터: 색상, 가격, 브랜드 등 필터링 조건
    
    예시:
    사용자 질문: "5만원 이내의 노란색 자켓 추천해줘"
    → search_query: "자켓"
    → search_parameters: "color=YELLOW&maxPrice=50000"
    """
    
    search_query: str = Field(
        description="핵심 검색어 (상품명, 카테고리 등 기본 검색 키워드)"
    )
    search_parameters: str = Field(
        description="검색 필터 파라미터 (URL 쿼리 문자열 형태: color=YELLOW&maxPrice=50000)"
    )


class QueryNodes:
    """Nodes for query analysis and handling with streaming support"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        """
        쿼리 분석 노드 초기화
        
        Args:
            model_name: 사용할 LLM 모델명 (기본: gpt-4.1)
        """
        self.llm = load_chat_model(model_name)
    
    def analyze_query(self, state) -> dict:
        """
        사용자 쿼리 분석으로 검색 필요성 판단
        
        Args:
            state: 사용자 메시지가 포함된 상태
            
        Returns:
            dict: 쿼리 타입(search_required/general)과 단계 정보
        """
        
        try:
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", QUERY_ANALYSIS_PROMPT),
                ("user", "{query}")
            ])
            
            # Use structured output to ensure only valid responses
            structured_llm = self.llm.with_structured_output(QueryAnalysisOutput)
            result = structured_llm.invoke(analysis_prompt.format_messages(query=state["messages"][-1].content))            
            print(f"Query analysis result: {result.query_type}")
            
            return {
                "query_type": result.query_type,
                "current_step": "query_analyzed"
            }
        except Exception as e:
            print(f"Error in analyze_query: {e}")
            # Default to general for any parsing errors - safer and simpler
            print("Using fallback classification: general")
            return {
                "query_type": "general",
                "current_step": "query_analyzed"
            }
    
    def handle_general_query(self, state) -> dict:
        """
        대화 내역을 활용한 일반 쿼리 처리
        
        Args:
            state: 대화 내역이 포함된 상태
            
        Returns:
            dict: 최종 응답, 업데이트된 메시지, 단계 정보
        """
        
        try:
            general_prompt = ChatPromptTemplate.from_messages([
                ("system", GENERAL_QUERY_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ])
            
            result = self.llm.invoke(general_prompt.format_messages(
                messages=state["messages"]
            ))
            
            print(f"General query result: {result.content[:100]}...")
            
            return {
                "final_response": result.content,
                "messages": [AIMessage(content=result.content)],
                "current_step": "completed"
            }
        except Exception as e:
            print(f"Error in handle_general_query: {e}")
            return {
                "final_response": "안녕하세요! 무엇을 도와드릴까요?",
                "messages": [AIMessage(content="안녕하세요! 무엇을 도와드릴까요?")],
                "current_step": "completed"
            }
    
    # TODO: 검색어 최적화 로직을 독립된 Optimizer 클래스로 분리 가능
    def optimize_search_query(self, state) -> dict:
        """
        사용자 질문을 Musinsa 검색에 최적화된 형태로 변환
        
        자연어 질문을 분석하여:
        1. 핵심 검색어 (상품명/카테고리) 추출
        2. 검색 필터 파라미터 (색상, 가격, 브랜드 등) 생성
        
        Args:
            state: 사용자 메시지가 포함된 상태 객체
            
        Returns:
            dict: 
                search_query 핵심 검색어 
                search_parameters (최적화된 검색 파라미터)를 포함한 상태 업데이트
            
        Example:
            Input: "5만원 이내의 노란색 자켓 추천해줘"
            Output: {
                "search_query": "자켓"
                "search_parameters": "color=YELLOW&maxPrice=50000",
                "current_step": "search_optimized"
            }
        """
        
        # 브랜드 코드를 시스템 프롬프트에 포함
        enhanced_prompt = SEARCH_QUERY_OPTIMIZATION_PROMPT.format(
            BRAND_CODES=format_brand_codes_for_prompt()
        )
        
        query_prompt = ChatPromptTemplate.from_messages([
            ("system", enhanced_prompt),
            ("human", "{query}")
        ])

        try:
            structured_llm = self.llm.with_structured_output(QueryOptimizationOutput)
            result = structured_llm.invoke(query_prompt.format(query=state["messages"][-1].content))
            
            print(f"Search query optimization result: {result.search_query}, parameters: {result.search_parameters}")
            
            return {
                "search_query": result.search_query,
                "search_parameters": result.search_parameters,
                "current_step": "search_optimized"
            }
        except Exception as e:
            print(f"Error in optimize_search_query: {e}")
            # Extract basic search terms as fallback
            user_query = state["messages"][-1].content
            return {
                "search_query": user_query,
                "search_parameters": "",
                "current_step": "search_optimized"
            }