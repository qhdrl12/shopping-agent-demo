"""
Response generation nodes
"""

import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..prompts.system_prompts import (
    NO_RESULTS_RESPONSE_PROMPT,
    FINAL_RESPONSE_PROMPT
)


class ResponseNodes:
    """Nodes for generating final responses"""
    
    def __init__(self, model_name: str = "gpt-4.1"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
    
    def generate_final_response(self, state) -> dict:
        """Generate final response considering conversation history"""
        
        print("Starting final response generation...")

        if not state.get("product_data"):
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
            formatted_prompt = response_prompt.format_messages(
                messages=state["messages"],
                products=json.dumps(state["product_data"], ensure_ascii=False, indent=2)
            )
        
        # Generate response using LLM
        try:
            result = self.llm.invoke(formatted_prompt)
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
                "messages": AIMessage(content=error_message),
                "current_step": "completed"
            }
    
