"""
Search and filtering nodes
"""

import re
from urllib.parse import urlparse
from typing import List

from ..tools.firecrawl_tools import search_musinsa, scrape_product_page
from urllib.parse import parse_qs, urlencode



class SearchNodes:
    """Nodes for product search and filtering"""
    
    def _remove_category_from_params(self, search_parameters: str) -> str:
        """검색 파라미터에서 category 관련 정보를 제거"""
        if not search_parameters:
            return ""
        
        try:
            # URL 파라미터 파싱
            params = parse_qs(search_parameters)
            
            # category 관련 파라미터 제거
            category_keys = [key for key in params.keys() if 'category' in key.lower()]
            for key in category_keys:
                del params[key]
            
            # 남은 파라미터들을 다시 문자열로 변환
            filtered_params = {}
            for key, values in params.items():
                if values and values[0]:  # 빈 값이 아닌 경우만
                    filtered_params[key] = values[0]
            
            return urlencode(filtered_params) if filtered_params else ""
            
        except Exception as e:
            print(f"Error removing category from params: {e}")
            return search_parameters  # 에러 시 원본 반환


    def search_products(self, state) -> dict:
        """
        Enhanced fallback search strategy:
        1. First try scrape_product_page for direct product search
        2. If no results and category exists, retry without category
        3. Fallback to search_musinsa for site-wide search only if still no results
        4. Return unique links
        """
        
        print(f"Starting search parameters: {state['search_parameters']}")
        
        search_query = state["search_query"]
        search_parameters = state["search_parameters"]
        search_results = []
        
        try:
            print(f"Sequential search for query: {search_query}")
            
            # 전략 1: 직접 상품 페이지 스크래핑 (가장 빠르고 정확한 방법)
            # Musinsa 검색 결과 페이지를 직접 스크래핑하여 상품 링크 추출
            direct_results = scrape_product_page.invoke({
                "query": search_query,
                "query_terms": search_parameters
            })
            if direct_results:
                print(f"Found {len(direct_results)} products via direct scraping for: {search_query}")
                search_results = direct_results
            else:
                # 전략 1-2: category가 포함된 경우 category 제거 후 재검색
                if search_parameters and 'category' in search_parameters.lower():
                    print("No results with category, trying without category...")
                    params_without_category = self._remove_category_from_params(search_parameters)
                    print(f"Retrying with parameters: {params_without_category}")
                    
                    direct_results_no_category = scrape_product_page.invoke({
                        "query": search_query,
                        "query_terms": params_without_category
                    })
                    if direct_results_no_category:
                        print(f"Found {len(direct_results_no_category)} products without category for: {search_query}")
                        search_results = direct_results_no_category
                
                # 전략 2: 여전히 결과가 없으면 Firecrawl의 사이트 검색 API 사용 (폴백 방법)
                if not search_results:
                    print("No results from direct scraping, trying site search...")
                    site_results = search_musinsa.invoke(search_query)
                    if site_results:
                        print(f"Found {len(site_results)} products via site search for: {search_query}")
                        search_results = site_results
                    else:
                        print("No results found from any search method")
                        search_results = []
            
        except Exception as e:
            # 검색 중 오류 발생 시 로깅하고 빈 결과 반환
            print(f"Search error for query '{search_query}': {e}")
            import traceback
            traceback.print_exc()
            search_results = []
        

        # 중복 URL 제거 (순서 유지)
        # 검색 결과에서 동일한 상품이 중복될 수 있으므로
        # set을 사용해 중복을 추적하면서 리스트 순서는 유지
        seen = set()
        unique_results = []
        for url in search_results:
            if url not in seen:
                seen.add(url)
                unique_results.append(url)
        
        print(f"Total unique results found: {len(unique_results)}")
        
        # Prepare search metadata for frontend display
        search_metadata = {
            "search_query": search_query,
            "search_parameters": search_parameters,
            "results_count": len(unique_results),
            "search_url": f"https://www.musinsa.com/search/musinsa/goods?q={search_query}"
        }
        
        # Add parameters to search URL if they exist
        if search_parameters:
            from urllib.parse import urlencode, parse_qs
            try:
                params = parse_qs(search_parameters)
                url_params = {"q": search_query}
                for key, values in params.items():
                    if values and values[0]:
                        url_params[key] = values[0]
                search_metadata["search_url"] = f"https://www.musinsa.com/search/musinsa/goods?{urlencode(url_params)}"
            except:
                pass  # Fall back to basic URL
        
        return {
            "search_results": unique_results,
            "search_metadata": search_metadata,
            "current_step": "search_completed"
        }


    # def search_products(self, state) -> dict:
    #     """
    #     Enhanced async search strategy:
    #     1. First try scrape_product_page for direct product search (parallel)
    #     2. Fallback to search_musinsa for site-wide search (parallel)
    #     3. If still no results, expand query and retry scrape_product_page (parallel)
    #     """
        
    #     print(f"Starting search terms: {state['optimized_search_terms']}")
        
    #     search_results = []
        
    #     # 3단계 검색 전략을 각 키워드에 대해 순차적으로 실행
    #     # 비동기 처리가 실패할 경우의 폴백 메커니즘
    #     for keyword in state['search_keywords']:
    #         try:
    #             print(f"Sequential search for keyword: {keyword}")
                
    #             # 전략 1: 직접 상품 페이지 스크래핑 (가장 빠르고 정확한 방법)
    #             # Musinsa 검색 결과 페이지를 직접 스크래핑하여 상품 링크 추출
    #             direct_results = scrape_product_page.invoke(keyword)
    #             if direct_results:
    #                 print(f"Found {len(direct_results)} products via direct scraping for: {keyword}")
    #                 search_results.extend(direct_results)
    #                 continue  # 결과를 찾았으므로 다음 키워드로 진행
                
    #             # 전략 2: Firecrawl의 사이트 검색 API 사용 (폴백 방법)
    #             # 직접 스크래핑이 실패했을 때 사용하는 대안적 검색 방법
    #             site_results = search_musinsa.invoke(keyword)
    #             if site_results:
    #                 print(f"Found {len(site_results)} products via site search for: {keyword}")
    #                 search_results.extend(site_results)
    #                 continue  # 결과를 찾았으므로 다음 키워드로 진행
                
    #             # 전략 3: 쿼리 확장 후 재검색 (최후의 수단)
    #             # 원본 키워드로 결과가 없을 때 유사한 키워드들로 확장하여 재시도
    #             print(f"No results found for '{keyword}', trying expanded queries...")
    #             expanded_queries = self._expand_query(keyword)
                
    #             for expanded_query in expanded_queries:
    #                 print(f"Trying expanded query: '{expanded_query}'")
    #                 expanded_results = scrape_product_page.invoke(expanded_query)
    #                 if expanded_results:
    #                     print(f"Found {len(expanded_results)} products via expanded query '{expanded_query}'")
    #                     search_results.extend(expanded_results)
    #                     break  # 하나의 확장 쿼리에서 결과를 찾았으므로 중단
                    
    #         except Exception as e:
    #             # 개별 키워드 검색 중 오류 발생 시 로깅하고 다음 키워드 계속 처리
    #             # 전체 검색 프로세스가 중단되지 않도록 예외 처리
    #             print(f"Search error for keyword '{keyword}': {e}")
    #             import traceback
    #             traceback.print_exc()
    #             continue  # 오류가 발생해도 다음 키워드 검색 계속 진행
        

    #     # 중복 URL 제거 (순서 유지)
    #     # 여러 키워드 검색이나 확장 쿼리에서 동일한 상품이 중복될 수 있으므로
    #     # set을 사용해 중복을 추적하면서 리스트 순서는 유지
    #     seen = set()
    #     unique_results = []
    #     for url in search_results:
    #         if url not in seen:
    #             seen.add(url)
    #             unique_results.append(url)
        
    #     print(f"Total unique results found: {len(unique_results)}")
    #     return {
    #         "search_results": unique_results,
    #         "current_step": "search_completed"
    #     }
    
    def filter_product_links(self, state) -> dict:
        """Filter and validate product links"""
        
        print(f"Filtering {len(state['search_results'])} search results...")
        
        product_links = []
        
        for url in state['search_results']:
            # Check if URL is a valid product page
            if self._is_product_url(url):
                product_links.append(url)
        
        return {
            "filtered_product_links": product_links[:5],  # Limit to 10 products
            "current_step": "links_filtered"
        }
    
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
    
    # TODO 해당 로직 점거 필요. 불필요하다면 제거 후 Optimzation 으로 변환 (2025-07-22)
    def _expand_query(self, original_query: str) -> List[str]:
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