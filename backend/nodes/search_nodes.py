"""
Search and filtering nodes
"""

import re
import asyncio
import concurrent.futures
from urllib.parse import urlparse
from ..tools.firecrawl_tools import search_musinsa, scrape_product_page


class SearchNodes:
    """Nodes for product search and filtering"""
    
    def search_products(self, state) -> dict:
        """
        Enhanced async search strategy:
        1. First try scrape_product_page for direct product search (parallel)
        2. Fallback to search_musinsa for site-wide search (parallel)
        3. If still no results, expand query and retry scrape_product_page (parallel)
        """
        
        # Set initial search state
        state.current_step = "search_products"
        
        async def search_single_keyword(keyword: str) -> list:
            """Search for a single keyword with fallback strategies"""
            try:
                # Strategy 1: Direct product page scraping
                print(f"Trying direct scraping for keyword: {keyword}")
                direct_results = await asyncio.get_event_loop().run_in_executor(
                    None, scrape_product_page.invoke, keyword
                )
                if direct_results:
                    print(f"Found {len(direct_results)} products via direct scraping for: {keyword}")
                    return direct_results
                
                # Strategy 2: Site-wide search as fallback
                print(f"Direct scraping failed, trying site search for: {keyword}")
                site_results = await asyncio.get_event_loop().run_in_executor(
                    None, search_musinsa.invoke, {"query": keyword, "num_results": 5}
                )
                if site_results:
                    print(f"Found {len(site_results)} products via site search for: {keyword}")
                    return site_results
                
                # Strategy 3: Expand query and retry direct scraping (parallel expanded queries)
                expanded_queries = self._expand_query(keyword)
                if expanded_queries:
                    print(f"Trying {len(expanded_queries)} expanded queries for: {keyword}")
                    
                    # Run all expanded queries in parallel
                    expanded_tasks = [
                        asyncio.get_event_loop().run_in_executor(
                            None, scrape_product_page.invoke, expanded_query
                        ) for expanded_query in expanded_queries
                    ]
                    
                    expanded_results = await asyncio.gather(*expanded_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(expanded_results):
                        if isinstance(result, list) and result:
                            print(f"Found {len(result)} products via expanded query '{expanded_queries[i]}'")
                            return result
                
            except Exception as e:
                print(f"Search error for keyword '{keyword}': {e}")
            
            return []
        
        async def search_all_keywords():
            """Search all keywords in parallel"""
            tasks = [search_single_keyword(keyword) for keyword in state.search_keywords]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_results = []
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
            
            return all_results
        
        # Update state to show search is starting
        print(f"Starting search for {len(state.search_keywords)} keywords: {state.search_keywords}")
        
        # Run async search
        try:
            if asyncio.get_event_loop().is_running():
                # If already in an async context, create a new event loop
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, search_all_keywords())
                    search_results = future.result()
            else:
                search_results = asyncio.run(search_all_keywords())
        except:
            # Fallback to sequential processing if async fails
            print("Async search failed, falling back to sequential processing")
            search_results = []
            for keyword in state.search_keywords:
                try:
                    print(f"Sequential search for keyword: {keyword}")
                    direct_results = scrape_product_page.invoke(keyword)
                    if direct_results:
                        search_results.extend(direct_results)
                        continue
                    
                    site_results = search_musinsa.invoke({"query": keyword, "num_results": 5})
                    if site_results:
                        search_results.extend(site_results)
                        continue
                    
                    expanded_queries = self._expand_query(keyword)
                    for expanded_query in expanded_queries:
                        expanded_results = scrape_product_page.invoke(expanded_query)
                        if expanded_results:
                            search_results.extend(expanded_results)
                            break
                        
                except Exception as e:
                    print(f"Search error for keyword '{keyword}': {e}")
                    continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for url in search_results:
            if url not in seen:
                seen.add(url)
                unique_results.append(url)
        
        state.search_results = unique_results
        state.current_step = "search_completed"
        
        print(f"Total unique results found: {len(unique_results)}")
        return state
    
    def filter_product_links(self, state) -> dict:
        """Filter and validate product links"""
        
        # Set initial filtering state
        state.current_step = "filter_product_links"
        print(f"Filtering {len(state.search_results)} search results...")
        
        product_links = []
        
        for url in state.search_results:
            # Check if URL is a valid product page
            if self._is_product_url(url):
                product_links.append(url)
        
        state.filtered_product_links = product_links[:10]  # Limit to 10 products
        state.current_step = "links_filtered"
        
        return state
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL is a valid Musinsa product page"""
        try:
            parsed = urlparse(url)
            if 'musinsa.com' not in parsed.netloc:
                return False
            
            # Check for product-specific patterns
            product_patterns = [
                r'/product/',
                r'/products/',
                r'/goods/',
                r'/item/'
            ]
            
            # Exclude event/campaign/brand pages
            exclude_patterns = [
                r'/event/',
                r'/campaign/',
                r'/brand(?!/.*/product)',
                r'/category/',
                r'/search/',
                r'/sale/',
                r'/ranking/'
            ]
            
            path = parsed.path.lower()
            
            # Check if it matches product patterns
            has_product_pattern = any(re.search(pattern, path) for pattern in product_patterns)
            
            # Check if it matches exclude patterns
            has_exclude_pattern = any(re.search(pattern, path) for pattern in exclude_patterns)
            
            return has_product_pattern and not has_exclude_pattern
            
        except Exception:
            return False
    
    def _expand_query(self, original_query: str) -> list[str]:
        """
        Expand search query with related terms and variations
        
        Args:
            original_query: Original search keyword
            
        Returns:
            List of expanded search queries
        """
        expanded_queries = []
        
        # Common Korean fashion terms mapping
        fashion_expansions = {
            # Outerwear
            "코트": ["롱코트", "숏코트", "트렌치코트", "울코트", "캐시미어코트"],
            "자켓": ["블레이저", "재킷", "아우터", "점퍼"],
            "패딩": ["다운", "점퍼", "롱패딩", "숏패딩"],
            
            # Tops
            "티셔츠": ["반팔", "긴팔", "맨투맨", "티", "반팔티", "긴팔티"],
            "셔츠": ["블라우스", "남방", "와이셔츠"],
            "후드": ["후드티", "후디", "맨투맨"],
            
            # Bottoms
            "바지": ["팬츠", "슬랙스", "청바지", "데님"],
            "스커트": ["치마", "미니스커트", "롱스커트"],
            "반바지": ["숏팬츠", "쇼츠"],
            
            # Colors
            "블랙": ["검정", "검은색", "black"],
            "화이트": ["흰색", "하얀색", "white"],
            "네이비": ["남색", "navy"],
            "베이지": ["beige", "카키"],
            
            # Materials
            "울": ["wool", "모직", "양모"],
            "코튼": ["cotton", "면", "순면"],
            "실크": ["silk", "비단"],
            "데님": ["denim", "청"],
        }
        
        query_lower = original_query.lower()
        
        # Add variations based on mapping
        for base_term, variations in fashion_expansions.items():
            if base_term in query_lower:
                for variation in variations:
                    expanded_query = original_query.replace(base_term, variation)
                    if expanded_query != original_query:
                        expanded_queries.append(expanded_query)
        
        # Add general variations
        general_variations = [
            f"남성 {original_query}",
            f"여성 {original_query}",
            f"{original_query} 남자",
            f"{original_query} 여자",
            f"{original_query} 브랜드",
            f"추천 {original_query}",
        ]
        
        # Add only relevant general variations (limit to avoid too many requests)
        expanded_queries.extend(general_variations[:2])
        
        # Remove duplicates and limit results
        unique_expansions = list(set(expanded_queries))
        
        # Return top 3 expansions to avoid excessive API calls
        return unique_expansions[:3]