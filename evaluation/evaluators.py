"""
Enhanced Shopping Agent Evaluators

Based on the reference implementation but improved for the Musinsa shopping agent:
- Uses 0-100 point scale for each metric
- LLM-based evaluation with structured prompts
- Domain-specific criteria for shopping agents
- Comprehensive error handling and debugging
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI


class EvaluationResult(BaseModel):
    """Structured evaluation result"""
    total_score: float = Field(description="총 점수 (0-100 범위)", ge=0, le=100)
    reasoning: str = Field(description="평가 근거 및 세부 설명")


class BaseEvaluator:
    """Base class for all evaluators"""
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        self.model = model or ChatOpenAI(
            model="gpt-4o",
            temperature=0.1
        )
    
    def __call__(self, run, example):
        """Make evaluator callable for LangSmith"""
        print(f"example: {example}")
        inputs = example.inputs if hasattr(example, 'inputs') else run.inputs
        outputs = run.outputs if hasattr(run, 'outputs') else run
        return self.evaluate(inputs, outputs)
        
    async def _safe_evaluate_async(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Safely evaluate with structured output and error handling (async version)"""
        try:
            # Use structured output for reliable score extraction
            structured_llm = self.model.with_structured_output(EvaluationResult)
            result = await structured_llm.ainvoke(prompt)
            
            return {
                "score": result.total_score,
                "reasoning": result.reasoning,
                "success": True,
                "error": None
            }
        except Exception as e:
            return {
                "score": 0.0,
                "reasoning": f"평가 중 오류 발생: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _safe_evaluate(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Safely evaluate with structured output and error handling (sync version for compatibility)"""
        try:
            # Use structured output for reliable score extraction
            structured_llm = self.model.with_structured_output(EvaluationResult)
            result = structured_llm.invoke(prompt)
            
            return {
                "score": result.total_score,
                "reasoning": result.reasoning,
                "success": True,
                "error": None
            }
        except Exception as e:
            return {
                "score": 0.0,
                "reasoning": f"평가 중 오류 발생: {str(e)}",
                "success": False,
                "error": str(e)
            }


class WorkflowExecutionEvaluator(BaseEvaluator):
    """
    Evaluates the workflow execution quality
    Based on tool selection and execution efficiency
    """
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        super().__init__(model)
        self.name = "workflow_execution"
        self.max_score = 100
    
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                 reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate workflow execution based on:
        - Query type classification accuracy (25점)
        - Search query optimization quality (25점) 
        - Filtering accuracy (25점)
        - Error handling and recovery (25점)
        """
        
        query = inputs.get("query", "")
        query_type = outputs.get("query_type", "")
        search_query = outputs.get("search_query", "")
        current_step = outputs.get("current_step", "")
        
        # Extract enhanced tracking data for better evaluation
        execution_trace = outputs.get("execution_trace", {})
        workflow_stats = outputs.get("workflow_stats", {})
        messages = outputs.get("messages", [])
        tool_calls = execution_trace.get("tool_calls", [])
        nodes_executed = execution_trace.get("nodes_executed", [])
        execution_path = workflow_stats.get("execution_path", [])
        
        # Extract filtering data for accuracy evaluation
        search_results = outputs.get("search_results", [])
        filtered_links = outputs.get("filtered_product_links", [])
        product_data = outputs.get("product_data", [])
        
        search_count = len(search_results) if search_results else 0
        filtered_count = len(filtered_links) if filtered_links else 0
        extracted_count = len(product_data) if product_data else 0
        
        prompt = f"""
당신은 쇼핑 에이전트의 워크플로우 실행 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
분류된 쿼리 타입: {query_type}
생성된 검색 쿼리: "{search_query}"
현재 단계: {current_step}

=== 상세 실행 정보 ===
실행 경로: {' → '.join(execution_path)}
총 실행 단계: {workflow_stats.get('total_steps', 0)}개
도구 호출 횟수: {len(tool_calls)}회
생성된 메시지 수: {len(messages)}개

=== 필터링 결과 ===
검색 결과 수: {search_count}개
필터링된 링크 수: {filtered_count}개
추출된 상품 수: {extracted_count}개
필터링 비율: {(filtered_count/search_count*100) if search_count > 0 else 0:.1f}%

도구 호출 상세:
{json.dumps(tool_calls, ensure_ascii=False, indent=2)}

노드 실행 순서:
{json.dumps([{'node': n['node'], 'step': n['step'], 'current_step': n['current_step']} for n in nodes_executed], ensure_ascii=False, indent=2)}

다음 기준으로 워크플로우 실행을 평가해주세요 (총 100점):

1. 쿼리 타입 분류 정확성 (25점)
   - general vs search_required 분류가 적절한가?
   - 사용자 의도를 정확히 파악했는가?

2. 검색 쿼리 최적화 품질 (25점)
   - 원본 쿼리가 무신사 검색에 적합하게 변환되었는가?
   - 중요한 키워드가 보존되었는가?
   - 불필요한 단어가 제거되었는가?

3. 필터링 정확성 (25점)
   - 검색 결과에서 상품 링크를 정확히 필터링했는가?
   - 관련성 없는 결과를 적절히 제거했는가?

4. 오류 처리 및 복구 (25점)
   - 예외 상황을 잘 처리했는가?
   - 적절한 fallback 전략이 있는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 쿼리 타입 분류: [0-25점]
- 검색 쿼리 최적화: [0-25점]  
- 필터링 정확성: [0-25점]
- 오류 처리: [0-25점]

평가 이유:
[각 항목별 평가 근거를 구체적으로 설명]
"""
        
        result = self._safe_evaluate(prompt, {
            "query": query,
            "query_type": query_type,
            "search_query": search_query,
            "current_step": current_step
        })
        
        return {
            "key": self.name,
            "score": result["score"] / 100.0,  # Normalize to 0-1
            "comment": result["reasoning"]
        }


class SearchAccuracyEvaluator(BaseEvaluator):
    """
    Evaluates search and filtering accuracy
    """
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        super().__init__(model)
        self.name = "search_accuracy"
        self.max_score = 100
    
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                 reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate search accuracy based on:
        - Query relevance (60점)
        - Result availability (40점)
        """
        
        query = outputs.get("query", "")
        search_results = outputs.get("search_results", [])
        filtered_links = outputs.get("filtered_product_links", [])
        search_metadata = outputs.get("search_metadata", {})
        
        search_count = len(search_results) if search_results else 0
        filtered_count = len(filtered_links) if filtered_links else 0
        
        # 검색 쿼리와 파라미터 분석
        search_query = search_metadata.get('search_query', '')
        search_params = search_metadata.get('search_parameters', '')
        search_url = search_metadata.get('search_url', 'N/A')
        
        prompt = f"""
당신은 쇼핑 에이전트의 검색 정확도를 평가하는 전문가입니다.

=== 사용자 요청 분석 ===
사용자 쿼리: "{query}"

=== 시스템 검색 수행 내역 ===
검색어: "{search_query}"
검색 파라미터: {search_params if search_params else '없음'}
최종 검색 URL: {search_url}
검색 결과: {search_count}개 상품 페이지 발견
유효 링크: {filtered_count}개 상품 링크 확보

다음 기준으로 검색 정확도를 평가해주세요 (총 100점):

1. 쿼리 해석 및 변환 품질 (60점)
   - 사용자 의도를 정확히 파악했는가?
   - 핵심 키워드가 누락되지 않았는가?
   - 가격, 브랜드, 카테고리 등 조건이 올바르게 적용되었는가?
   - 불필요하거나 잘못된 검색어가 포함되지 않았는가?
   
   🚨 논리 오류 패널티 (심각도별):
   - minPrice > maxPrice 같은 논리적 모순: -40점 (치명적 오류)
   - 사용자 의도와 정반대 결과를 초래하는 오류: -35점
   - 음수 가격, 비현실적 가격(1억원 이상): -20점  
   - 브랜드 필드에 숫자나 특수문자만: -15점
   - 존재하지 않는 파라미터나 잘못된 형식: -10점
   
   ⚠️ 중요: 논리 오류로 인해 사용자 요청과 완전히 다른 상품이 
   검색되는 경우 해당 검색은 "실패"로 간주
   
   평가 기준 (패널티 적용 후):
   - 완벽한 의도 파악 + 적절한 파라미터: 55-60점
   - 대체로 적절하지만 일부 부족: 40-54점  
   - 핵심 내용 누락 또는 부적절한 변환: 20-39점
   - 의도와 다른 검색 또는 중요 조건 무시: 0-19점
   - 논리 오류가 있는 경우: 위 점수에서 패널티 차감

2. 검색 결과 확보 (40점)
   - 충분한 상품을 찾을 수 있었는가?
   - 3개 이상: 만점(40점), 1-2개: 20점, 0개: 0점

현재 검색 성과: {filtered_count}개 상품 확보 {'(충분)' if filtered_count >= 3 else '(부족)' if filtered_count > 0 else '(실패)'}

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 쿼리 해석 및 변환 품질: [0-60점]
- 검색 결과 확보: [0-40점]

평가 이유:
[다음 순서로 체계적으로 분석하되, 동일한 오류에 대해 중복 언급 금지]

1. 사용자 의도 파악 정확성
   - 핵심 키워드 인식 여부
   - 가격, 브랜드 등 조건 이해도

2. 검색어 및 파라미터 변환 품질  
   - 검색어 적절성
   - 파라미터 설정의 정확성
   - **논리 오류 검증 포함** (minPrice vs maxPrice, 의도 일치성 등)

3. 패널티 적용 (해당되는 경우만)
   - 발견된 오류 유형과 심각도
   - 적용된 패널티 점수와 이유
   - 사용자 경험에 미치는 영향

4. 최종 종합 평가
   - 기본 점수 산정 근거
   - 패널티 차감 후 최종 점수
   - 개선 방향 제안

⚠️ 주의: 동일한 오류(예: 가격 범위 모순)를 여러 항목에서 반복 언급하지 말고, 
한 번만 명확히 기술하여 패널티 적용
"""
        
        result = self._safe_evaluate(prompt, {
            "query": query,
            "search_count": search_count,
            "filtered_count": filtered_count
        })
        
        return {
            "key": self.name,
            "score": result["score"] / 100.0,
            "comment": result["reasoning"]
        }


class DataExtractionEvaluator(BaseEvaluator):
    """
    Evaluates product data extraction quality
    """
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        super().__init__(model)
        self.name = "data_extraction"
        self.max_score = 100
    
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                 reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate data extraction based on:
        - Extraction success rate (50점)
        - Information completeness (25점)
        - Data accuracy (15점)
        - Structured formatting (10점)
        """
        
        query = inputs.get("query", "")
        product_data = outputs.get("product_data", [])
        
        product_count = len(product_data) if product_data else 0
        
        # Extract success rate: 시스템 정책을 고려한 추출 성공률
        filtered_links = outputs.get("filtered_product_links", [])
        total_attempted = len(filtered_links)
        
        # 시스템 정책: 최대 3개 상품만 사용자에게 제공
        max_system_limit = 3
        effective_attempted = min(total_attempted, max_system_limit)
        
        # 실제 추출 성공 개수 (시스템 제한 전)
        raw_extracted = outputs.get("extracted_products_count", product_count)
        # 시스템 제한을 고려한 성공 개수
        successfully_extracted = min(raw_extracted, max_system_limit) if raw_extracted else product_count
        
        success_rate = (successfully_extracted / effective_attempted) if effective_attempted > 0 else 0.0
        
        # Check required fields
        required_fields = ["name", "price", "original_price", "discount_info", "reward_points", "images"]
        optional_fields = ["shipping_info", "size_info", "stock_status", "rating", "colors", "description", "features", "review_count"]
        
        completeness_stats = []
        if product_data:
            for i, product in enumerate(product_data, 1):
                required_present = sum(1 for field in required_fields if product.get(field))
                optional_present = sum(1 for field in optional_fields if product.get(field))
                completeness_stats.append({
                    "product_index": i,
                    "required": required_present,
                    "optional": optional_present,
                    "completeness_ratio": f"{required_present}/{len(required_fields)}"
                })
        
        # Format product data for display
        formatted_products = ""
        for i, product in enumerate(product_data, 1):
            formatted_products += f"\n{i}. 상품{i} 추출 데이터\n{json.dumps(product, ensure_ascii=False, indent=2)}\n"
        
        prompt = f"""
당신은 쇼핑 에이전트의 상품 데이터 추출 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"

=== 시스템 정책 ===
- 사용자에게는 최대 3개 상품만 제공 (응답 속도 및 품질 최적화)
- 실제로는 더 많은 상품을 추출할 수 있음

=== 추출 결과 ===
전체 검색된 링크: {total_attempted}개
시스템 처리 대상: {effective_attempted}개 (최대 3개 제한)
실제 추출 성공: {raw_extracted if raw_extracted else 'N/A'}개
사용자 제공: {successfully_extracted}개
추출 성공률: {success_rate:.1%} (처리 대상 기준)

추출한 상품 데이터:{formatted_products}

완성도 통계:
- 필수 필드: {required_fields}
- 선택 필드: {optional_fields}
- 각 상품별 완성도: {completeness_stats}

다음 기준으로 데이터 추출 품질을 평가해주세요 (총 100점):

1. 추출 성공률 (50점)
   - 시스템 처리 대상 상품 대비 성공적으로 데이터를 추출한 비율
   - 시스템 정책: 속도/품질 최적화를 위해 최대 3개까지만 처리
   - 100%: 50점, 80%: 40점, 60%: 30점, 40%: 20점, 20%: 10점, 0%: 0점
   - 현재 성공률: {success_rate:.1%} ({successfully_extracted}/{effective_attempted})

2. 정보 완성도 (25점)
   - 필수 정보(상품명, 가격, 브랜드, 이미지, URL)가 모두 추출되었는가?
   - 추가 정보(설명, 카테고리, 색상 등)도 포함되어 있는가?

3. 데이터 정확성 (15점)
   - 추출된 정보가 정확하고 일관성이 있는가?
   - 가격 형식이 올바른가?
   - URL이 유효한가?

4. 구조화된 형식 (10점)
   - 데이터가 일관된 형식으로 구조화되어 있는가?
   - 필드명이 명확하고 표준화되어 있는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 추출 성공률: [0-50점]
- 정보 완성도: [0-25점]
- 데이터 정확성: [0-15점]
- 구조화된 형식: [0-10점]

평가 이유:
[각 항목별 평가 근거를 구체적으로 설명]
"""
        
        result = self._safe_evaluate(prompt, {
            "query": query,
            "product_count": product_count,
            "completeness_stats": completeness_stats
        })
        
        return {
            "key": self.name,
            "score": result["score"] / 100.0,
            "comment": result["reasoning"]
        }


class ResponseQualityEvaluator(BaseEvaluator):
    """
    Evaluates final response quality and helpfulness
    """
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        super().__init__(model)
        self.name = "response_quality"
        self.max_score = 100
    
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                 reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate response quality based on:
        - Recommendation appropriateness (35점)
        - Information usefulness (30점)
        - Response comprehensiveness (25점)
        - Practical actionability (10점)
        """
        
        query = inputs.get("query", "")
        final_response = outputs.get("final_response", "")
        suggested_questions = outputs.get("suggested_questions", [])
        product_data = outputs.get("product_data", [])
        
        # Enhanced tracking data
        messages = outputs.get("messages", [])
        execution_trace = outputs.get("execution_trace", {})
        workflow_stats = outputs.get("workflow_stats", {})
        
        response_length = len(final_response)
        suggestion_count = len(suggested_questions) if suggested_questions else 0
        product_count = len(product_data) if product_data else 0
        message_count = len(messages)
        
        prompt = f"""
당신은 쇼핑 에이전트의 최종 응답 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
최종 응답 길이: {response_length}자
제안된 질문 수: {suggestion_count}개
포함된 상품 수: {product_count}개
총 메시지 수: {message_count}개

최종 응답:
{final_response}

제안된 질문들:
{json.dumps(suggested_questions, ensure_ascii=False, indent=2)}

=== 대화 흐름 분석 ===
메시지 추적 (최근 5개):
{json.dumps(messages[-5:] if messages else [], ensure_ascii=False, indent=2)}

상품 정보 샘플 (최대 3개):
{json.dumps(product_data[:3] if product_data else [], ensure_ascii=False, indent=2)}

다음 기준으로 응답 품질을 평가해주세요 (총 100점):

1. 추천 적절성 (35점)
   - 사용자의 요구사항에 맞는 상품을 추천했는가?
   - 추천 이유가 명확하고 설득력이 있는가?
   - 다양한 옵션을 제공했는가?

2. 정보 유용성 (30점)
   - 구매 결정에 도움이 되는 정보를 제공했는가?
   - 가격, 브랜드, 특징 등 핵심 정보가 포함되어 있는가?
   - 정보가 명확하고 이해하기 쉬운가?

3. 응답 포괄성 (25점)
   - 사용자 질문에 완전히 답변했는가?
   - 추가적으로 도움이 될 만한 정보를 제공했는가?
   - 전체적인 구성이 논리적인가?

4. 실용적 실행가능성 (10점)
   - 실제 구매로 이어질 수 있는 구체적인 정보를 제공했는가?
   - 다음 단계에 대한 안내가 있는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 추천 적절성: [0-35점]
- 정보 유용성: [0-30점]
- 응답 포괄성: [0-25점]
- 실용적 실행가능성: [0-10점]

평가 이유:
[각 항목별 평가 근거를 구체적으로 설명]
"""
        
        result = self._safe_evaluate(prompt, {
            "query": query,
            "response_length": response_length,
            "suggestion_count": suggestion_count,
            "product_count": product_count
        })
        
        return {
            "key": self.name,
            "score": result["score"] / 100.0,
            "comment": result["reasoning"]
        }


class OverallPerformanceEvaluator(BaseEvaluator):
    """
    Evaluates overall performance including latency and user experience
    """
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        super().__init__(model)
        self.name = "overall_performance"  
        self.max_score = 100
    
    def evaluate(self, inputs: Dict[str, Any], outputs: Dict[str, Any], 
                 reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate overall performance based on:
        - Execution speed (30점)
        - Error handling (25점)
        - User experience (25점)
        - System reliability (20점)
        """
        
        query = inputs.get("query", "")
        execution_time = outputs.get("execution_time", 0)
        query_type = outputs.get("query_type", "")
        
        # Performance thresholds based on query type
        if query_type == "general":
            excellent_threshold = 5.0
            good_threshold = 10.0
            acceptable_threshold = 20.0
        else:
            excellent_threshold = 15.0
            good_threshold = 30.0
            acceptable_threshold = 60.0
        
        prompt = f"""
당신은 쇼핑 에이전트의 전체적인 성능을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
쿼리 타입: {query_type}
실행 시간: {execution_time:.2f}초

성능 기준:
- 우수: {excellent_threshold}초 이하
- 양호: {good_threshold}초 이하  
- 허용: {acceptable_threshold}초 이하

다음 기준으로 전체 성능을 평가해주세요 (총 100점):

1. 실행 속도 (30점)
   - 응답 시간이 사용자 기대치에 부합하는가?
   - 쿼리 타입에 적절한 처리 시간인가?

2. 오류 처리 (25점)
   - 시스템이 안정적으로 작동했는가?
   - 예외 상황을 적절히 처리했는가?

3. 사용자 경험 (25점)
   - 전체적인 사용자 경험이 만족스러운가?
   - 응답이 사용자 친화적인가?

4. 시스템 신뢰성 (20점)
   - 일관된 품질의 결과를 제공하는가?
   - 예측 가능한 동작을 보이는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 실행 속도: [0-30점]
- 오류 처리: [0-25점]
- 사용자 경험: [0-25점]
- 시스템 신뢰성: [0-20점]

평가 이유:
[각 항목별 평가 근거를 구체적으로 설명]
"""
        
        result = self._safe_evaluate(prompt, {
            "query": query,
            "execution_time": execution_time,
            "query_type": query_type
        })
        
        return {
            "key": self.name,
            "score": result["score"] / 100.0,
            "comment": result["reasoning"]
        }


class ParallelEvaluatorManager:
    """Manager for parallel evaluation execution"""
    
    def __init__(self):
        self.evaluators = [
            SearchAccuracyEvaluator(), 
            DataExtractionEvaluator(),
            ResponseQualityEvaluator(),
            # OverallPerformanceEvaluator()
        ]
    
    async def evaluate_parallel(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run all evaluators in parallel for maximum performance
        """
        print(f"🚀 Starting parallel evaluation with {len(self.evaluators)} evaluators...")
        
        # Create async tasks for all evaluators
        tasks = []
        for evaluator in self.evaluators:
            task = self._run_evaluator_async(evaluator, inputs, outputs)
            tasks.append(task)
        
        # Execute all evaluations in parallel
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        print(f"⚡ Parallel evaluation completed in {end_time - start_time:.2f}s")
        
        # Process results and handle any exceptions
        evaluation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Evaluator {self.evaluators[i].name} failed: {result}")
                evaluation_results.append({
                    "key": self.evaluators[i].name,
                    "score": 0.0,
                    "comment": f"평가 실패: {str(result)}"
                })
            else:
                evaluation_results.append(result)
                print(f"✅ {result['key']}: {result['score']:.3f}")
        
        return evaluation_results
    
    async def _run_evaluator_async(self, evaluator, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single evaluator asynchronously
        """
        try:
            # Run evaluator in a thread pool to avoid blocking
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(evaluator.evaluate, inputs, outputs)
                result = await loop.run_in_executor(None, lambda: future.result())
            
            return result
        except Exception as e:
            raise Exception(f"Evaluation failed for {evaluator.name}: {str(e)}")


# Create parallel evaluator manager instance
parallel_manager = ParallelEvaluatorManager()

# 모든 평가자를 하나의 리스트로 정의 (기존 호환성 유지)
EVALUATORS = [
    SearchAccuracyEvaluator(), 
    DataExtractionEvaluator(),
    ResponseQualityEvaluator(),
    # OverallPerformanceEvaluator()
]


def get_evaluators():
    """Get all evaluators for the shopping agent"""
    return EVALUATORS


def get_parallel_evaluators():
    """Get parallel evaluator manager"""
    return parallel_manager