"""
Firecrawl Tools for Musinsa Product Scraping

This module provides LangChain tools for searching and scraping product information
from Musinsa (Korean fashion e-commerce platform) using the Firecrawl API.

Tools included:
- search_musinsa: Search for products on Musinsa website
- scrape_product_page: Basic scraping of product pages
- extract_product_info: Structured product data extraction

Required environment variables:
- FIRECRAWL_API_KEY: API key for Firecrawl service
"""

import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from firecrawl import FirecrawlApp
from langchain_core.tools import tool
# from ..models.schemas import ProductInfo, SearchQuery

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Firecrawl app with API key
# Firecrawl is a web scraping service that converts web pages to structured data
api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    raise ValueError("FIRECRAWL_API_KEY environment variable is required")
firecrawl_app = FirecrawlApp(api_key=api_key)

def extract_product_links(html: str) -> List[str]:
    """
    Extract product links from Musinsa HTML content.
    
    This function parses HTML and extracts all links (href attributes) that contain 'products'
    in their URL path. It returns a list of unique product URLs found in the HTML.
    
    Args:
        html (str): HTML content to parse for product links
        
    Returns:
        List[str]: List of unique product URLs containing 'products' in the path
        
    Example:
        >>> html = '<a href="https://www.musinsa.com/products/1234567">Product</a>'
        >>> extract_product_links(html)
        ['https://www.musinsa.com/products/1234567']
    """
    if not html:
        return []
    
    # Pattern to match href attributes that contain 'products'
    # This will match both relative and absolute URLs
    href_pattern = r'href="([^"]*products[^"]*)"'
    
    # Find all matching href attributes
    matches = re.findall(href_pattern, html, re.IGNORECASE)
    # print(f"matches : {matches}")
    
    # Convert relative URLs to absolute URLs and filter unique ones
    product_links = []
    for match in matches:
        if match.startswith('/'):
            # Convert relative URL to absolute URL
            full_url = f"https://www.musinsa.com{match}"
        elif match.startswith('https://www.musinsa.com'):
            # Already absolute URL
            full_url = match
        else:
            # Skip other types of URLs
            continue
            
        if full_url not in product_links:
            product_links.append(full_url)
    
    return product_links

@tool
def search_musinsa(query: str, num_results: int = 5) -> List[str]:
    """
    Search for products on Musinsa website using Firecrawl's search API.
    
    This function searches for products on the Musinsa e-commerce platform by
    using site-specific search queries. It returns a list of product URLs that
    match the search criteria.
    
    Args:
        query (str): Search query string (e.g., "나이키 운동화", "겨울 코트")
        num_results (int, optional): Number of results to return. Defaults to 5.
                                   Maximum recommended is 10 for performance.
    
    Returns:
        List[str]: List of product URLs from Musinsa. Returns empty list on error.
    
    Example:
        >>> urls = search_musinsa("나이키 에어맥스", 3)
        >>> print(urls)
        ['https://www.musinsa.com/product/1234567', ...]
    """
    try:
        # Use Firecrawl's search API with site-specific query
        result = firecrawl_app.search(
            query=f"site:musinsa.com {query}",
            limit=num_results
        )
        
        print(f"search_musinsa result: {result}")

        # Extract URLs from the search results
        urls = []
        if result and 'data' in result:
            for item in result['data']:
                if 'url' in item:
                    urls.append(item['url'])
        
        return urls
    except Exception as e:
        # Firecrawl 검색 API 오류 발생 시 처리
        # API 제한, 네트워크 오류, 인증 문제 등을 포함
        # 빈 리스트를 반환하여 다른 검색 전략으로 폴백할 수 있도록 함
        print(f"Error searching Musinsa: {e}")
        import traceback
        traceback.print_exc()
        return []  # 빈 리스트 반환으로 graceful degradation 수행

@tool
def scrape_product_page(query: str, query_terms: Optional[str]) -> List[str]:
    """
    Search for products on Musinsa by scraping search results page and extracting product links.
    
    This function performs a direct search on Musinsa's search page using the provided query,
    then extracts all product links from the search results. It's designed to be the primary
    search method in the 3-tier search strategy, providing fast access to product URLs
    without requiring separate search API calls.
    
    Args:
        query (str): Search query string for finding products on Musinsa.
                    Examples: "롱코트", "나이키 운동화", "검은색 자켓"
    
    Returns:
        List[str]: List of product URLs found in the search results.
                  Returns empty list if no products found or on error.
                  URLs are in format: https://www.musinsa.com/products/{product_id}
    
    Example:
        >>> result = scrape_product_page('롱코트')
        >>> print(f"Found {len(result)} products")
        Found 15 products
        >>> print(result[0])
        'https://www.musinsa.com/products/1684196'
    
    Note:
        This function is part of the enhanced 3-tier search strategy:
        1. First try scrape_product_page (this function) for direct product search
        2. Fallback to search_musinsa for site-wide search if no results
        3. Expand query and retry scrape_product_page if still no results
    """
    try:
        params = {'q' : query}

        if query_terms:
            if isinstance(query_terms, dict):
                params.update(query_terms)
            elif isinstance(query_terms, str):
                from urllib.parse import parse_qs
                additional_params = parse_qs(query_terms)
                for key, values in additional_params.items():
                    if values and values[0]:
                        params[key] = values[0]

        url = f"https://www.musinsa.com/search/musinsa/goods?{urlencode(params)}"
        print(f"search url: {url}")

        # Use Firecrawl's scrape_url method with optimized parameters for faster scraping
        result = firecrawl_app.scrape_url(
            url=url,
            formats=['html'],
            include_tags=['a'],
            exclude_tags=['script', 'style', 'noscript', 'iframe'],
            wait_for=3000,  # Reduced wait time for faster response
            only_main_content=True  # Focus on main content to reduce processing time
        )
        # print(f"Scraping completed for result: {result}")
        
        # Extract product links from HTML
        html_content = result.html if hasattr(result, 'html') else ''
        product_links = extract_product_links(html_content)
        
        # Return structured response with all extracted data (limit to 5 for better performance)
        return product_links[:5] if len(product_links) >= 5 else product_links
    except Exception as e:
        # 스크래핑 중 오류 발생 시 처리
        # Firecrawl API 오류 (502 Bad Gateway 등), 네트워크 오류, 파싱 오류 등을 포함
        # 빈 리스트를 반환하여 상위 로직에서 다른 검색 전략을 시도할 수 있도록 함
        print(f"Error scraping {query}: {e}")
        import traceback
        traceback.print_exc()
        return []  # 빈 리스트 반환으로 graceful degradation 수행

@tool
def extract_product_info(url: str) -> str:
    """
    Extract structured product information from a Musinsa product page.
    
    This function uses Firecrawl's AI-powered extraction to convert unstructured
    product page content into structured JSON data according to a predefined schema.
    This is the most important function for getting consistent product data.
    
    Args:
        url (str): The URL of the Musinsa product page to extract data from.
                  Must be a valid HTTP/HTTPS URL.
    
    Returns:
        dict | str: Dictionary containing structured product information, or error message string.
                   The dictionary includes: name, price, original_price, discount_info, 
                   reward_points, shipping_info, size_info, stock_status, images, 
                   rating, colors, description, features, review_count.
    
    Schema:
        The extraction follows this JSON schema:
        - name (string): Product name
        - price (number): Current selling price in KRW
        - original_price (number): Original price before discount (if available)
        - discount_info (string): Discount percentage or amount
        - reward_points (number): Points earned when purchasing
        - shipping_info (string): Shipping information
        - size_info (string): Available sizes
        - stock_status (string): Stock availability status
        - images (array): Product image URLs (all available images)
        - rating (number): Product rating (1-5 scale)
        - colors (array): Available color options
        - description (string): Product description
        - features (array): Key product features
        - review_count (number): Number of customer reviews
    
    Example:
        >>> result = extract_product_info('https://www.musinsa.com/products/1234567')
        >>> print(result)
        {'name': '나이키 에어맥스 90', 'price': 139000, 'original_price': 159000, ...}
    """
    try:
        print(f"start extract_product_info : {url}")
        # Define JSON schema for structured product data extraction
        # This schema ensures consistent data format across all extractions
        product_schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name or title of the product"
                },
                "price": {
                    "type": "number",
                    "description": "Current selling price of the product (numeric value only, without currency symbols)"
                },
                "original_price": {
                    "type": "number", 
                    "description": "Original price before discount (if available)"
                },
                "discount_info": {
                    "type": "string",
                    "description": "Discount percentage or amount (e.g., '20%', '5000원 할인')"
                },
                "reward_points": {
                    "type": "number",
                    "description": "Points earned when purchasing this product"
                },
                "shipping_info": {
                    "type": "string",
                    "description": "Shipping information (e.g., '무료배송', '2500원')"
                },
                "size_info": {
                    "type": "string", 
                    "description": "Available sizes (e.g., 'S, M, L, XL', '250-280mm')"
                },
                "stock_status": {
                    "type": "string",
                    "description": "Stock availability status (e.g., '재고있음', '품절')"
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Product image URLs - extract ALL product images including main image, detail shots, model wearing shots, color variations. Return as many relevant images as available."
                },
                "rating": {
                    "type": "number",
                    "description": "Product rating (1-5 scale)"
                },
                "colors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Available color options"
                },
                "description": {
                    "type": "string",
                    "description": "Product description"
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key product features"
                },
                "review_count": {
                    "type": "number",
                    "description": "Number of customer reviews"
                },
            },
            "required": ["name", "price"]
        }
        
         
        result = firecrawl_app.scrape_url(
            url, 
            formats=["extract"],
            extract={
                "prompt": """Extract key product information: name, price, original_price, discount_info, reward_points (적립금/포인트), shipping_info, size_info, stock_status, images, rating, review_count. 
                
                IMPORTANT for images: Extract ALL product images including:
                - Main product image
                - Detail shots showing product features
                - Model wearing the product (if available)
                - Different color variations
                - Multiple angles/views of the product
                
                Look for reward points information typically displayed near the price section as '적립금' or '포인트'.
                Look for rating information (stars or numerical score) and review count (리뷰, 후기 등).
                Return as JSON with only available fields.""",
                "schema": product_schema
            },
            only_main_content=True,
            wait_for=2000  # Reduced wait time for faster extraction
        )
        
        extracted_data = result.extract
        # Process and return the extracted data
        if extracted_data.get('name') and extracted_data.get('price'):
            return extracted_data
        else:
            return f"Could not extract product info from {url}"
            
    except Exception as e:
        # 상품 정보 추출 중 오류 발생 시 처리
        # Firecrawl API 장애, 잘못된 URL, 파싱 실패 등의 경우를 포함
        # 에러 메시지를 문자열로 반환하여 상위 로직에서 에러임을 인식할 수 있도록 함
        print(f"Error extracting product info from {url}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error extracting product info from {url}: {e}"  # 에러 메시지 반환

# List of all tools for easy import by agents
# This allows agents to import all tools at once: from .firecrawl_tools import firecrawl_tools
firecrawl_tools = [search_musinsa, scrape_product_page, extract_product_info]


if __name__ == "__main__":
    # Test with the HTML you provided    
    print("\nActual scraping result:")
    result = scrape_product_page.invoke("나이키 운동화")
    print(f"result: {result}")
    # print(f"Found {len(result.get('product_links', []))} product links:")
    for link in result[:10]:  # Show first 10 links
        print(f"  - {link}")
