"""
Response generation nodes with streaming support
"""

import json
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..prompts.system_prompts import (
    NO_RESULTS_RESPONSE_PROMPT,
    FINAL_RESPONSE_PROMPT
)


class ResponseNodes:
    """Nodes for generating final responses with streaming support"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0, streaming=True)
    
    def generate_final_response(self, state) -> dict:
        """Synchronous version for backward compatibility"""
        
        # Set initial response generation state
        state.current_step = "generate_final_response"
        print("Starting final response generation...")
        
        if not state.product_data:
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", NO_RESULTS_RESPONSE_PROMPT),
                ("human", "User query: {query}")
            ])
            
            result = self.llm.invoke(response_prompt.format(query=state.user_query))
            state.final_response = result.content
        else:
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", FINAL_RESPONSE_PROMPT),
                ("human", "User query: {query}\n\nSelected products: {products}")
            ])
            
            result = self.llm.invoke(response_prompt.format(
                query=state.user_query,
                products=json.dumps(state.product_data, ensure_ascii=False, indent=2)
            ))
            state.final_response = result.content
        
        state.current_step = "completed"
        return state