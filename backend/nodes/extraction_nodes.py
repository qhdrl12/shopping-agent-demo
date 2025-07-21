"""
Data extraction and validation nodes
"""

import asyncio
import json
from typing import List
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
            for result in results:
                if isinstance(result, dict) and result is not None:
                    valid_products.append(result)
            
            print(f"🎉 Parallel extraction completed: {len(valid_products)}/{len(state['filtered_product_links'])} products extracted successfully")
            return valid_products        
        
        product_data = asyncio.run(extract_all_products(state['filtered_product_links']))

        return {
            "product_data": product_data,
            "current_step": "data_extracted"
        }
    
    def validate_and_select(self, state) -> dict:
        """Validate and select relevant products"""
        
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
            # Filter product_data to only include selected products
            selected_products = [state["product_data"][i] for i in selected_indices if i < len(state["product_data"])]
            product_data = selected_products
        except (json.JSONDecodeError, IndexError):
            # Fallback: keep all products
            product_data = state["product_data"]
        
        return {
            "product_data": product_data,
            "current_step": "products_selected"
        }