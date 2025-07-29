"""
Data extraction and validation nodes
"""

import asyncio
import json
from typing import List

from langchain_core.prompts import ChatPromptTemplate

from ..utils.model import load_chat_model
from ..tools.firecrawl_tools import extract_product_info
from ..prompts.system_prompts import PRODUCT_VALIDATION_PROMPT


class ExtractionNodes:
    """Nodes for product data extraction and validation"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        """
        데이터 추출 노드 초기화
        
        Args:
            model_name: 사용할 LLM 모델명 (기본: openai/gpt-4.1)
        """
        self.llm = load_chat_model(model_name)
    
    def extract_product_data(self, state) -> dict:
        """
        병렬로 상품 데이터 추출
        
        Args:
            state: 필터링된 상품 링크 리스트가 포함된 상태
            
        Returns:
            dict: 추출된 상품 데이터와 단계 정보
        """
        
        async def extract_all_products(urls: List[str]):
            """Extract data from all product URLs in parallel"""
            print(f"🚀 Starting parallel extraction for {len(urls)} products")
            # Create tasks with index for better tracking
            tasks = [
                extract_product_info.ainvoke(url)
                for url in urls
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_products = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Error extracting product {i}: {result}")
                    continue
                
                print(f"🔍 Product {i} result type: {type(result)}, content: {str(result)[:100]}...")
                
                if isinstance(result, dict) and result:
                    valid_products.append(result)
                    print(f"✅ Product {i}: Successfully added")
                else:
                    print(f"❌ Product {i}: Filtered out (empty or invalid)")
            
            print(f"🎉 Parallel extraction completed: {len(valid_products)}/{len(state['filtered_product_links'])} products extracted successfully")
            return valid_products        
        
        product_data = asyncio.run(extract_all_products(state['filtered_product_links']))

        return {
            "product_data": product_data,
            "extracted_products_count": len(product_data),  # 실제 추출 성공 개수 기록
            "current_step": "data_extracted"
        }
    
    def validate_and_select(self, state) -> dict:
        """
        상품 데이터 검증 및 관련 상품 선택
        
        Args:
            state: 추출된 상품 데이터가 포함된 상태
            
        Returns:
            dict: 선택된 상품 데이터(최대 3개)와 단계 정보
        """
        
        if not state.get("product_data"):
            return {"current_step": "no_valid_data"}
        
        validation_prompt = ChatPromptTemplate.from_messages([
            ("system", PRODUCT_VALIDATION_PROMPT),
            ("human", "User query: {query}\n\nProduct data: {products}")
        ])
        
        products_summary = []
        for i, product in enumerate(state["product_data"]):
            summary = f"{i}: {product.get('name', 'Unknown')} - {product.get('price', 'No price')}"
            products_summary.append(summary)
        
        result = self.llm.invoke(validation_prompt.format(
            query=state["messages"][-1].content,
            products="\n".join(products_summary)
        ))
        
        try:
            selected_indices = json.loads(result.content)
            # Validate indices and filter products
            product_data_list = state["product_data"]
            selected_products = [
                product_data_list[i] for i in selected_indices 
                if isinstance(i, int) and 0 <= i < len(product_data_list)
            ]
            # 최대 3개 상품으로 제한 (응답 품질 및 속도 최적화)
            selected_products = selected_products[:3]
            product_data = selected_products if selected_products else product_data_list[:3]
        except (json.JSONDecodeError, IndexError, TypeError) as e:
            print(f"Product selection error: {e}, keeping first 3 products")
            product_data = state["product_data"][:3]
        
        # 원본 추출 성공 개수 보존 (평가를 위해)
        original_extracted_count = state.get("extracted_products_count", len(state.get("product_data", [])))
        
        print(f"🔍 validate_and_select debug:")
        print(f"  Input product_data count: {len(state.get('product_data', []))}")
        print(f"  Input extracted_products_count: {state.get('extracted_products_count', 'Not found')}")
        print(f"  Selected product_data count: {len(product_data)}")
        print(f"  Final extracted_products_count: {original_extracted_count}")
        
        return {
            "product_data": product_data,
            "extracted_products_count": original_extracted_count,  # 원본 추출 성공 개수 보존
            "current_step": "products_selected"
        }