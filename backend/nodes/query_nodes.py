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
    KEYWORD_EXTRACTION_PROMPT
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
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Use structured output to ensure only valid responses
        structured_llm = self.llm.with_structured_output(QueryAnalysisOutput)
        result = structured_llm.invoke(analysis_prompt.format_messages(messages=state["messages"]))
        
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
        
        result = self.llm.invoke(general_prompt.format_messages(messages=state["messages"]))
        
        # Add AI response to messages for multi-turn conversation
        
        return {
            "final_response": result.content,
            "messages": [AIMessage(content=result.content)],
            "current_step": "completed"
        }
    
    def extract_search_keywords(self, state) -> dict:
        """Extract search keywords from the current query"""
        retry_count = 3
        
        keyword_prompt = ChatPromptTemplate.from_messages([
            ("system", KEYWORD_EXTRACTION_PROMPT),
            ("human", "Query: {query}\nRetry count: {retry_count}")
        ])
        
        result = self.llm.invoke(keyword_prompt.format(
            query=state["messages"][-1].content,
            retry_count=retry_count
        ))
        
        try:
            keywords = json.loads(result.content)
            if not isinstance(keywords, list):
                raise ValueError("Keywords should be a list")
            
            # On retry, reduce keywords to broaden search
            if retry_count > 0 and keywords:
                keywords = keywords[:max(1, len(keywords) - retry_count)]
            
            search_keywords = keywords if keywords else [state["messages"][-1].content]
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Keyword extraction error: {e}")
            search_keywords = [state["messages"][-1].content if state["messages"] else ""]
        
        return {
            "search_keywords": search_keywords,
            "current_step": "keywords_extracted"
        }