"""
Response generation nodes
"""

import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage

from ..utils.model import load_chat_model

from ..prompts.system_prompts import (
    NO_RESULTS_RESPONSE_PROMPT,
    FINAL_RESPONSE_PROMPT
)


class ResponseNodes:
    """Nodes for generating final responses"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        """
        응답 생성 노드 초기화
        
        Args:
            model_name: 사용할 LLM 모델명 (기본: gpt-4.1)
        """
        self.llm = load_chat_model(model_name)
        # 실시간 스트리밍을 위한 모델 인스턴스
        self.streaming_llm = load_chat_model(model_name, streaming=True)
    
    def generate_final_response(self, state) -> dict:
        """
        대화 내역을 고려하여 최종 응답 생성
        
        Args:
            state: 대화 상태 (메시지, 상품 데이터 포함)
            
        Returns:
            dict: 최종 응답, 업데이트된 메시지, 단계 정보
        """
        
        print("Starting final response generation...")

        # Handle both legacy (product_data) and new (search_results) workflow formats
        products = state.get("product_data") or state.get("search_results", [])
        
        if not products:
            # 검색 결과가 없을 때, 전체 대화 기록을 바탕으로 답변 생성
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", NO_RESULTS_RESPONSE_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ])
            formatted_prompt = response_prompt.format_messages(messages=state["messages"])
        else:
            # 검색 결과가 있을 때, 대화 기록과 상품 정보를 함께 전달
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", FINAL_RESPONSE_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
                ("human", "검색된 상품 정보를 참고하여 답변해주세요:\n\n{products}")
            ])
            # Safely handle products serialization
            try:
                products_str = json.dumps(products, ensure_ascii=False, indent=2)
            except (TypeError, ValueError) as e:
                print(f"Warning: Failed to serialize products: {e}")
                products_str = str(products)
            
            formatted_prompt = response_prompt.format_messages(
                messages=state["messages"],
                products=products_str
            )
        
        # Generate response using streaming LLM for real-time token streaming
        try:
            result = self.streaming_llm.invoke(formatted_prompt)
            print(f"Response generation completed. Total length: {len(result.content)}")
            
            # Add AI response to messages for multi-turn conversation
            return {
                "final_response": result.content,
                "messages": [AIMessage(content=result.content)],
                "current_step": "completed"
            }
        except Exception as e:
            print(f"Response generation failed: {e}")
            error_message = "응답 생성 중 오류가 발생했습니다."
            
            return {
                "final_response": error_message,
                "messages": [AIMessage(content=error_message)],  # 리스트 형태로 수정
                "current_step": "completed"
            }
    
    
