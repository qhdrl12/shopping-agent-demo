"""
Unified Shopping Agent Workflow

This module implements a single LangGraph workflow that handles the complete shopping assistance process:
1. User query analysis
2. Question classification (general vs. search-required)
3. Search execution with Firecrawl
4. Product link filtering and validation
5. Parallel product data extraction
6. Data quality validation and selection
7. Final response generation

The workflow uses a state-based approach with conditional routing for optimal performance.
"""

import operator
from typing import Dict, Any, List, Literal, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from ..nodes.query_nodes import QueryNodes
from ..nodes.search_nodes import SearchNodes
from ..nodes.extraction_nodes import ExtractionNodes
from ..nodes.response_nodes import ResponseNodes
from ..nodes.question_nodes import QuestionNodes


class WorkflowState(TypedDict):
    """Enhanced state model for the unified workflow"""
    
    # User input and query analysis
    messages: Annotated[List[BaseMessage], operator.add]
    query_type: Literal["general", "search_required"]
    
    # Search phase
    search_query: str
    search_parameters: str
    search_results: List[str]
    search_metadata: Dict[str, Any]  # Added for search information display
    filtered_product_links: List[str]
    
    # Data extraction phase  
    product_data: List[Dict[str, Any]]
    
    # Response generation
    final_response: str
    suggested_questions: List[str]
    
    # Workflow control
    current_step: str


class UnifiedShoppingWorkflow:
    """Main workflow class that orchestrates the shopping assistance process"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        self.query_nodes = QueryNodes(model_name)
        self.search_nodes = SearchNodes()
        self.extraction_nodes = ExtractionNodes(model_name)
        self.response_nodes = ResponseNodes(model_name)
        self.question_nodes = QuestionNodes(model_name)
        
        self.saver = InMemorySaver()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the complete workflow graph"""
        workflow = StateGraph(WorkflowState)
        
        # Add all workflow nodes
        workflow.add_node("analyze_query", self.query_nodes.analyze_query)
        workflow.add_node("handle_general_query", self.query_nodes.handle_general_query)
        workflow.add_node("optimize_search_query", self.query_nodes.optimize_search_query)
        workflow.add_node("search_products", self.search_nodes.search_products)
        workflow.add_node("filter_product_links", self.search_nodes.filter_product_links)
        workflow.add_node("extracting_product_details", self._set_extracting_status)
        workflow.add_node("extract_product_data", self.extraction_nodes.extract_product_data)
        workflow.add_node("validate_and_select", self.extraction_nodes.validate_and_select)
        workflow.add_node("generate_final_response", self.response_nodes.generate_final_response)
        workflow.add_node("generate_suggested_questions", self.question_nodes.generate_suggested_questions)
        
        # Set entry point
        workflow.set_entry_point("analyze_query")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_query",
            self._route_after_analysis,
            {
                "general": "handle_general_query",
                "search_required": "optimize_search_query"
            }
        )
        
        workflow.add_edge("handle_general_query", "generate_suggested_questions")
        workflow.add_edge("optimize_search_query", "search_products")
        workflow.add_edge("search_products", "filter_product_links")
        
        workflow.add_conditional_edges(
            "filter_product_links",
            self._route_after_filtering,
            {
                "extract_data": "extracting_product_details",
                "no_results": "generate_final_response"
            }
        )
        
        workflow.add_edge("extracting_product_details", "extract_product_data")
        workflow.add_edge("extract_product_data", "validate_and_select")
        
        workflow.add_conditional_edges(
            "validate_and_select",
            self._route_after_validation,
            {
                "generate_response": "generate_final_response"
            }
        )
        
        workflow.add_edge("generate_final_response", "generate_suggested_questions")
        workflow.add_edge("generate_suggested_questions", END)

        return workflow.compile(checkpointer=self.saver)
    
    def _route_after_analysis(self, state: WorkflowState) -> str:
        """Route based on query analysis"""
        return state["query_type"]
    
    def _route_after_filtering(self, state: WorkflowState) -> str:
        """Route based on filtered product links"""
        if not state["filtered_product_links"]:
            return "no_results"
        return "extract_data"
    
    def _route_after_validation(self, state: WorkflowState) -> str:
        """Route based on product validation"""
        # Always route to response generation after validation
        return "generate_response"
    
    def _set_extracting_status(self, state: WorkflowState) -> dict:
        """Set status to indicate product detail extraction is starting"""
        # Set extraction status regardless of current state
        return {"current_step": "extracting_product_details"}
    


# Create global workflow instance
unified_workflow = UnifiedShoppingWorkflow("openai/gpt-4.1")
# unified_workflow = UnifiedShoppingWorkflow("openrouter/google/gemini-2.5-flash")
# unified_workflow = UnifiedShoppingWorkflow("openrouter/qwen/qwen3-235b-a22b-07-25:free")

# Export compiled workflow for LangGraph Studio
workflow = unified_workflow.workflow