"""
Internal Scrape Shopping Agent Workflow

This module implements a new LangGraph workflow using internal scrape.py tools:
1. User query analysis
2. Question classification (general vs. search-required)
3. Search execution with search_detailed_products tool
4. Data compatibility parsing for legacy format
5. Final response generation

This workflow provides better performance and control over data extraction.
"""

# Load environment variables at module level to ensure they're available
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from backend.prompts.system_prompts import INTERNAL_SEARCH_QUERY_OPTIMIZATION_PROMPT
from backend.utils.model import load_chat_model
load_dotenv()

import operator
from typing import Dict, Any, List, Literal, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from ..nodes.query_nodes import QueryNodes
from ..nodes.response_nodes import ResponseNodes
from ..nodes.question_nodes import QuestionNodes
from ..tools.scrape import search_detailed_products


class InternalWorkflowState(TypedDict):
    """Enhanced state model for the internal scrape workflow"""
    
    # User input and query analysis
    messages: Annotated[List[BaseMessage], operator.add]
    query_type: Literal["general", "search_required"]
    
    # Search phase - optimized for internal tools
    search_query: str
    search_parameters: Dict[str, Any]  # Changed from str to Dict for internal tools
    search_results: List[Dict[str, Any]]  # Direct product data instead of URLs
    search_metadata: Dict[str, Any]
    
    # Response generation
    final_response: str
    suggested_questions: List[str]
    
    # Workflow control
    current_step: str

class SearchParameters(BaseModel):
    gender: str = Field(
        default="A",
        description="대상 성별 필터. M(남성), F(여성), A(전체). 원피스 등 특정 성별 아이템은 자동 추론 가능합니다.",
        examples=["M", "F", "A"]
    )
    minPrice: int = Field(
        default=0,
        ge=0,
        description="검색할 최소 가격 (원 단위). '5만원 이상', '10만원대' 등의 표현을 숫자로 변환합니다. 기본값 0은 가격 하한 없음을 의미합니다.",
        examples=[0, 50000, 100000, 200000]
    )
    maxPrice: int = Field(
        default=999999,
        description="검색할 최대 가격 (원 단위). '10만원 이하', '20만원대' 등의 표현을 숫자로 변환합니다. 기본값 999999는 가격 상한 없음을 의미합니다.",
        examples=[50000, 100000, 200000, 500000, 999999]
    )
    color: str = Field(
        default="",
        description="색상 필터. 한국어('검은색', '하얀색') 또는 영어('black', 'white') 색상을 표현합니다. 빈 문자열이면 모든 색상을 검색합니다.",
        examples=["BLACK", "WHITE", "NAVY", "GRAY", "RED"]
    )
    
    shoeSize: int = Field(
        default=0,
        description="신발 사이즈 (mm 단위). 신발 관련 검색어가 있을 때만 사용하며, 신발이 아닌 경우 반드시 0으로 설정해야 합니다.",
        examples=[0, 230, 250, 270, 280]
    )


class InternalQueryOptimizationOutput(BaseModel):
    
    search_query: str = Field(
        description="핵심 검색어 (상품명, 카테고리 등 기본 검색 키워드)"
    )
    search_parameters: SearchParameters = Field(
        description="검색 필터 파라미터"
    )


class InternalScrapeNodes:
    """Nodes specifically for internal scrape workflow"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        self.llm = load_chat_model(model_name)

    
    def optimize_search_query_internal(self, state) -> dict:
        """
        Optimize search query for internal scrape tools
        Converts search parameters to format expected by search_detailed_products
        """

        query_prompt = ChatPromptTemplate.from_messages([
            ("system", INTERNAL_SEARCH_QUERY_OPTIMIZATION_PROMPT),
            ("human", "{query}")
        ])

        try:
            structured_llm = self.llm.with_structured_output(InternalQueryOptimizationOutput)
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
    
    
    def search_products_internal(self, state) -> dict:
        """
        Search products using internal search_detailed_products tool
        """
        search_query = state["search_query"]
        search_params = state["search_parameters"]

        try:
            print(f"Searching with internal tool: {search_query}, params: {search_params}")
            
            # Call search_detailed_products tool with search_query as keyword
            search_dict = search_params.model_dump()
            search_dict["keyword"] = search_query  # Add search_query as keyword parameter
            result = search_detailed_products.invoke(search_dict)
            
            if result.get("success"):
                products = result.get("products", [])
                print(f"Found {len(products)} products via internal search")
                
                # Parse products to legacy-compatible format
                parsed_products = self._parse_to_legacy_format(products)
                print(f"Parsed products: {parsed_products}")
                
                search_metadata = {
                    "search_query": search_query,
                    "search_parameters": search_params,
                    "results_count": len(parsed_products),
                    "search_method": "internal_scrape"
                }
                
                return {
                    "search_results": parsed_products,
                    "search_metadata": search_metadata,
                    "current_step": "search_completed_internal"
                }
            else:
                print(f"Internal search failed: {result.get('error', 'Unknown error')}")
                return {
                    "search_results": [],
                    "search_metadata": {
                        "search_query": search_query,
                        "search_parameters": search_params,
                        "results_count": 0,
                        "error": result.get("error")
                    },
                    "current_step": "search_failed"
                }
                
        except Exception as e:
            print(f"Error in search_products_internal: {e}")
            return {
                "search_results": [],
                "search_metadata": {
                    "search_query": search_query,
                    "search_parameters": search_params,
                    "results_count": 0,
                    "error": str(e)
                },
                "current_step": "search_failed"
            }
    
    def _parse_to_legacy_format(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse internal scrape results to legacy format for compatibility
        
        Args:
            products: Results from search_detailed_products
            
        Returns:
            List of products in legacy format
        """
        legacy_products = []
        
        for product in products:
            try:
                # Map internal format to legacy format
                legacy_product = {
                    # Basic product info
                    "goods_no": str(product.get("goodsNo", "")),
                    "name": product.get("goodsName", ""),
                    "brand": product.get("brandName", ""),
                    "price": product.get("price", 0),
                    "original_price": product.get("normalPrice", 0),
                    "sale_rate": product.get("saleRate", 0),
                    "image_url": product.get("thumbnail", ""),
                    "product_url": product.get("goodsLinkUrl", ""),
                    "is_sold_out": product.get("isSoldOut", False),
                    
                    # Review info
                    "review_count": product.get("reviewCount", 0),
                    "review_score": product.get("reviewScore", 0),
                    
                    # Additional legacy fields
                    "gender": product.get("displayGenderText", ""),
                    "brand_code": product.get("brand", ""),
                    "brand_url": product.get("brandLinkUrl", ""),
                    "is_plus_delivery": product.get("isPlusDelivery", False),
                    
                    # Enhanced data from internal tool
                    "benefits": product.get("benefits", []),
                    "reviews": product.get("reviews", []),
                    "benefits_loaded": product.get("benefits_success", False),
                    "reviews_loaded": product.get("reviews_success", False),
                    
                    # Data source identifier
                    "data_source": "internal_scrape"
                }
                
                legacy_products.append(legacy_product)
                
            except Exception as e:
                print(f"Error parsing product to legacy format: {e}")
                continue
        
        return legacy_products


class InternalScrapeWorkflow:
    """Main workflow class for internal scrape-based shopping assistance"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        self.query_nodes = QueryNodes(model_name)
        self.internal_nodes = InternalScrapeNodes(model_name)
        self.response_nodes = ResponseNodes(model_name)
        self.question_nodes = QuestionNodes(model_name)
        
        self.saver = InMemorySaver()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the internal scrape workflow graph"""
        workflow = StateGraph(InternalWorkflowState)
        
        # Add workflow nodes
        workflow.add_node("analyze_query", self.query_nodes.analyze_query)
        workflow.add_node("handle_general_query", self.query_nodes.handle_general_query)
        workflow.add_node("optimize_search_query_internal", self.internal_nodes.optimize_search_query_internal)
        workflow.add_node("search_products_internal", self.internal_nodes.search_products_internal)
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
                "search_required": "optimize_search_query_internal"
            }
        )
        
        workflow.add_edge("handle_general_query", "generate_suggested_questions")
        workflow.add_edge("optimize_search_query_internal", "search_products_internal")
        
        workflow.add_conditional_edges(
            "search_products_internal",
            self._route_after_search,
            {
                "generate_response": "generate_final_response",
                "no_results": "generate_final_response"
            }
        )
        
        workflow.add_edge("generate_final_response", "generate_suggested_questions")
        workflow.add_edge("generate_suggested_questions", END)

        return workflow.compile(checkpointer=self.saver)
    
    def _route_after_analysis(self, state: InternalWorkflowState) -> str:
        """Route based on query analysis"""
        return state["query_type"]
    
    def _route_after_search(self, state: InternalWorkflowState) -> str:
        """Route based on search results"""
        if not state["search_results"]:
            return "no_results"
        return "generate_response"


# Create global internal workflow instance
internal_scrape_workflow = InternalScrapeWorkflow("openai/gpt-4.1")

# Export compiled workflow for use
internal_workflow = internal_scrape_workflow.workflow