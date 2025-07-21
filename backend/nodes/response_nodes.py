"""
Response generation nodes
"""

import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..prompts.system_prompts import (
    NO_RESULTS_RESPONSE_PROMPT,
    FINAL_RESPONSE_PROMPT
)


class ResponseNodes:
    """Nodes for generating final responses"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
    
    def generate_final_response(self, state) -> dict:
        """Generate final response"""
        
        # Set initial response generation state
        state.current_step = "generate_final_response"
        print("Starting final response generation...")
        
        if not state.product_data:
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", NO_RESULTS_RESPONSE_PROMPT),
                ("human", "User query: {query}")
            ])
            formatted_prompt = response_prompt.format(query=state.user_query)
        else:
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", FINAL_RESPONSE_PROMPT),
                ("human", "User query: {query}\n\nSelected products: {products}")
            ])
            formatted_prompt = response_prompt.format(
                query=state.user_query,
                products=json.dumps(state.product_data, ensure_ascii=False, indent=2)
            )
        
        # Generate response using LLM
        try:
            result = self.llm.invoke(formatted_prompt)
            state.final_response = result.content
            print(f"Response generation completed. Total length: {len(result.content)}")
        except Exception as e:
            print(f"Response generation failed: {e}")
            state.final_response = "응답 생성 중 오류가 발생했습니다."
        
        state.current_step = "completed"
        return state
    
