"""
Query analysis and handling nodes with streaming support
"""

import json
import asyncio
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..prompts.system_prompts import (
    QUERY_ANALYSIS_PROMPT,
    GENERAL_QUERY_PROMPT,
    KEYWORD_EXTRACTION_PROMPT
)


class QueryAnalysisOutput(BaseModel):
    """Structured output for query analysis"""
    query_type: Literal["search_required", "general"] = Field(
        description="Type of query: search_required for product searches, general for other queries"
    )


class QueryNodes:
    """Nodes for query analysis and handling with streaming support"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.streaming_llm = ChatOpenAI(model=model_name, temperature=0, streaming=True)
    
    def analyze_query(self, state) -> dict:
        """Analyze user query to determine if search is needed"""
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", QUERY_ANALYSIS_PROMPT),
            ("human", "{query}")
        ])
        
        # Use structured output to ensure only valid responses
        structured_llm = self.llm.with_structured_output(QueryAnalysisOutput)
        result = structured_llm.invoke(analysis_prompt.format(query=state.user_query))
        
        state.query_type = result.query_type
        state.current_step = "query_analyzed"
        
        return state
    
    def handle_general_query(self, state) -> dict:
        """Synchronous version for backward compatibility"""
        
        general_prompt = ChatPromptTemplate.from_messages([
            ("system", GENERAL_QUERY_PROMPT),
            ("human", "{query}")
        ])
        
        result = self.llm.invoke(general_prompt.format(query=state.user_query))
        state.final_response = result.content
        state.current_step = "completed"
        
        return state
    
    def extract_search_keywords(self, state) -> dict:
        """Extract search keywords from the query"""
        retry_count=3
        
        keyword_prompt = ChatPromptTemplate.from_messages([
            ("system", KEYWORD_EXTRACTION_PROMPT),
            ("human", "Query: {query}\nRetry count: {retry_count}")
        ])
        
        result = self.llm.invoke(keyword_prompt.format(
            query=state.user_query,
            retry_count=retry_count
        ))
        
        try:
            keywords = json.loads(result.content)
            # On retry, reduce keywords to broaden search
            if retry_count > 0:
                keywords = keywords[:max(1, len(keywords) - retry_count)]
            state.search_keywords = keywords
        except json.JSONDecodeError:
            # Fallback to simple keyword extraction
            state.search_keywords = [state.user_query]
        
        state.current_step = "keywords_extracted"
        return state