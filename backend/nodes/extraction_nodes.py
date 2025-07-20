"""
Data extraction and validation nodes
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..tools.firecrawl_tools import extract_product_info
from ..prompts.system_prompts import PRODUCT_VALIDATION_PROMPT


class ExtractionNodes:
    """Nodes for product data extraction and validation"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
    
    def extract_product_data(self, state) -> dict:
        """Extract product data in parallel"""
        
        async def extract_single_product(url: str) -> Optional[Dict[str, Any]]:
            """Extract data from a single product URL"""
            try:
                result = extract_product_info.invoke({"url": url})
                if isinstance(result, dict) and result.get('name'):
                    return result
                return None
            except Exception as e:
                print(f"Extraction error for {url}: {e}")
                return None
        
        async def extract_all_products():
            """Extract data from all product URLs in parallel"""
            tasks = [extract_single_product(url) for url in state.filtered_product_links]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_products = []
            for result in results:
                if isinstance(result, dict) and result is not None:
                    valid_products.append(result)
            
            return valid_products
        
        # Run async extraction
        try:
            import asyncio
            if asyncio.get_event_loop().is_running():
                # If already in an async context, create a new event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, extract_all_products())
                    product_data = future.result()
            else:
                product_data = asyncio.run(extract_all_products())
        except:
            # Fallback to sequential processing
            product_data = []
            for url in state.filtered_product_links:
                try:
                    result = extract_product_info.invoke({"url": url})
                    if isinstance(result, dict) and result.get('name'):
                        product_data.append(result)
                except Exception as e:
                    print(f"Extraction error for {url}: {e}")
                    continue
        
        state.product_data = product_data
        state.current_step = "data_extracted"
        
        return state
    
    def validate_and_select(self, state) -> dict:
        """Validate and select relevant products"""
        
        if not state.product_data:
            state.current_step = "no_valid_data"
            return state
        
        validation_prompt = ChatPromptTemplate.from_messages([
            ("system", PRODUCT_VALIDATION_PROMPT),
            ("human", "User query: {query}\n\nProduct data: {products}")
        ])
        
        products_summary = []
        for i, product in enumerate(state.product_data):
            summary = f"{i}: {product.get('name', 'Unknown')} - {product.get('price', 'No price')}"
            products_summary.append(summary)
        
        result = self.llm.invoke(validation_prompt.format(
            query=state.user_query,
            products="\n".join(products_summary)
        ))
        
        try:
            selected_indices = json.loads(result.content)
            # Filter product_data to only include selected products
            selected_products = [state.product_data[i] for i in selected_indices if i < len(state.product_data)]
            state.product_data = selected_products
        except (json.JSONDecodeError, IndexError):
            # Fallback: keep all products
            pass
        
        state.current_step = "products_selected"
        
        return state