"""
Query analysis and handling nodes with streaming support
"""

import json
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..prompts.system_prompts import (
    QUERY_ANALYSIS_PROMPT,
    GENERAL_QUERY_PROMPT,
    SEARCH_QUERY_OPTIMIZATION_PROMPT
)


class QueryAnalysisOutput(BaseModel):
    """Structured output for query analysis"""
    query_type: Literal["search_required", "general"] = Field(
        description="Type of query: search_required for product searches, general for other queries"
    )


class QueryNodes:
    """Nodes for query analysis and handling with streaming support"""
    
    def __init__(self, model_name: str = "gpt-4.1-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.streaming_llm = ChatOpenAI(model=model_name, temperature=0, streaming=True)
    
    def analyze_query(self, state) -> dict:
        """Analyze user query to determine if search is needed"""
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", QUERY_ANALYSIS_PROMPT),
            ("user", "{query}")
        ])
        
        # Use structured output to ensure only valid responses
        structured_llm = self.llm.with_structured_output(QueryAnalysisOutput)
        result = structured_llm.invoke(analysis_prompt.format(query=state["messages"][-1].content))
        
        return {
            "query_type": result.query_type,
            "current_step": "query_analyzed"
        }
    
    def handle_general_query(self, state) -> dict:
        """Handle general queries using conversation history"""
        
        general_prompt = ChatPromptTemplate.from_messages([
            ("system", GENERAL_QUERY_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        result = self.llm.invoke(general_prompt.format_messages(
            messages=state["messages"]
        ))
        
        return {
            "final_response": result.content,
            "messages": [AIMessage(content=result.content)],
            "current_step": "completed"
        }
    
    def optimize_search_query(self, state) -> dict:
        """Optimize user query into effective Musinsa search terms"""
        
        query_prompt = ChatPromptTemplate.from_messages([
            ("system", SEARCH_QUERY_OPTIMIZATION_PROMPT),
            ("human", "{query}")
        ])
        
        result = self.llm.invoke(query_prompt.format(
            query=state["messages"][-1].content,
        ))
        
        try:
            search_queries = json.loads(result.content)
            if not isinstance(search_queries, list):
                raise ValueError("Search queries should be a list")
            
            search_keywords = search_queries if search_queries else [state["messages"][-1].content]
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Search query optimization error: {e}")
            search_keywords = [state["messages"][-1].content if state["messages"] else ""]
        
        return {
            "search_keywords": search_keywords,
            "current_step": "search_optimized"
        }