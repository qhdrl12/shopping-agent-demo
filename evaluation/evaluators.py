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
from typing import Dict, Any, List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI


class BaseEvaluator:
    """Base class for all evaluators"""
    
    def __init__(self, model: Optional[BaseLanguageModel] = None):
        self.model = model or ChatOpenAI(
            model="gpt-4o",
            temperature=0.1
        )
    
    def __call__(self, run, example):
        """Make evaluator callable for LangSmith"""
        inputs = example.inputs if hasattr(example, 'inputs') else run.inputs
        outputs = run.outputs if hasattr(run, 'outputs') else run
        return self.evaluate(inputs, outputs)
    
    def _extract_score(self, response: str) -> float:
        """Extract score from LLM response using regex"""
        # Look for patterns like "점수: 85", "Score: 85", "총점: 85/100"
        patterns = [
            r'점수\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'Score\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'총점\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*[/／]\s*100',
            r'(\d+(?:\.\d+)?)\s*점'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 100.0)  # Clamp between 0 and 100
        
        return 0.0  # Default if no score found
    
    def _safe_evaluate(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Safely evaluate with error handling"""
        try:
            result = self.model.invoke(prompt)
            content = result.content
            score = self._extract_score(content)
            
            return {
                "score": score,
                "reasoning": content,
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
        - Tool usage efficiency (25점)
        - Error handling and recovery (25점)
        """
        
        query = inputs.get("query", "")
        query_type = outputs.get("query_type", "")
        search_query = outputs.get("search_query", "")
        current_step = outputs.get("current_step", "")
        
        prompt = f"""
당신은 쇼핑 에이전트의 워크플로우 실행 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
분류된 쿼리 타입: {query_type}
생성된 검색 쿼리: "{search_query}"
현재 단계: {current_step}

다음 기준으로 워크플로우 실행을 평가해주세요 (총 100점):

1. 쿼리 타입 분류 정확성 (25점)
   - general vs search_required 분류가 적절한가?
   - 사용자 의도를 정확히 파악했는가?

2. 검색 쿼리 최적화 품질 (25점)
   - 원본 쿼리가 무신사 검색에 적합하게 변환되었는가?
   - 중요한 키워드가 보존되었는가?
   - 불필요한 단어가 제거되었는가?

3. 도구 사용 효율성 (25점)
   - 적절한 워크플로우 경로를 선택했는가?
   - 불필요한 단계를 건너뛰었는가?

4. 오류 처리 및 복구 (25점)
   - 예외 상황을 잘 처리했는가?
   - 적절한 fallback 전략이 있는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 쿼리 타입 분류: [0-25점]
- 검색 쿼리 최적화: [0-25점]  
- 도구 사용 효율성: [0-25점]
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
        - Search result relevance (30점)
        - Filtering effectiveness (30점)
        - Product link quality (40점)
        """
        
        query = inputs.get("query", "")
        search_results = outputs.get("search_results", [])
        filtered_links = outputs.get("filtered_product_links", [])
        search_metadata = outputs.get("search_metadata", {})
        
        search_count = len(search_results) if search_results else 0
        filtered_count = len(filtered_links) if filtered_links else 0
        
        prompt = f"""
당신은 쇼핑 에이전트의 검색 정확도를 평가하는 전문가입니다.

사용자 쿼리: "{query}"
검색 결과 수: {search_count}개
필터링된 상품 링크 수: {filtered_count}개
검색 메타데이터: {json.dumps(search_metadata, ensure_ascii=False, indent=2)}

샘플 검색 결과 (최대 5개):
{json.dumps(search_results[:5], ensure_ascii=False, indent=2)}

샘플 필터링된 링크 (최대 5개):
{json.dumps(filtered_links[:5], ensure_ascii=False, indent=2)}

다음 기준으로 검색 정확도를 평가해주세요 (총 100점):

1. 검색 결과 관련성 (30점)
   - 검색된 결과가 사용자 쿼리와 얼마나 관련성이 있는가?
   - 무신사에서 적절한 검색이 수행되었는가?

2. 필터링 효과성 (30점)
   - 검색 결과에서 상품 링크를 얼마나 효과적으로 필터링했는가?
   - 불필요한 링크가 제거되었는가?

3. 상품 링크 품질 (40점)
   - 필터링된 링크가 실제 구매 가능한 상품 페이지인가?
   - 링크의 형식이 올바른가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 검색 결과 관련성: [0-30점]
- 필터링 효과성: [0-30점]
- 상품 링크 품질: [0-40점]

평가 이유:
[각 항목별 평가 근거를 구체적으로 설명]
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
        - Information completeness (40점)
        - Data accuracy (30점)
        - Structured formatting (30점)
        """
        
        query = inputs.get("query", "")
        product_data = outputs.get("product_data", [])
        
        product_count = len(product_data) if product_data else 0
        
        # Check required fields
        required_fields = ["name", "price", "brand", "image_url", "product_url"]
        optional_fields = ["description", "category", "color", "size", "rating"]
        
        completeness_stats = []
        if product_data:
            for product in product_data:
                required_present = sum(1 for field in required_fields if product.get(field))
                optional_present = sum(1 for field in optional_fields if product.get(field))
                completeness_stats.append({
                    "required": required_present,
                    "optional": optional_present
                })
        
        prompt = f"""
당신은 쇼핑 에이전트의 상품 데이터 추출 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
추출된 상품 수: {product_count}개

상품 데이터 샘플:
{json.dumps(product_data[:3], ensure_ascii=False, indent=2)}

완성도 통계:
- 필수 필드: {required_fields}
- 선택 필드: {optional_fields}
- 완성도 현황: {completeness_stats}

다음 기준으로 데이터 추출 품질을 평가해주세요 (총 100점):

1. 정보 완성도 (40점)
   - 필수 정보(상품명, 가격, 브랜드, 이미지, URL)가 모두 추출되었는가?
   - 추가 정보(설명, 카테고리, 색상 등)도 포함되어 있는가?

2. 데이터 정확성 (30점)
   - 추출된 정보가 정확하고 일관성이 있는가?
   - 가격 형식이 올바른가?
   - URL이 유효한가?

3. 구조화된 형식 (30점)
   - 데이터가 일관된 형식으로 구조화되어 있는가?
   - 필드명이 명확하고 표준화되어 있는가?

응답 형식:
점수: [0-100 사이의 점수]

세부 점수:
- 정보 완성도: [0-40점]
- 데이터 정확성: [0-30점]
- 구조화된 형식: [0-30점]

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
        
        response_length = len(final_response)
        suggestion_count = len(suggested_questions) if suggested_questions else 0
        product_count = len(product_data) if product_data else 0
        
        prompt = f"""
당신은 쇼핑 에이전트의 최종 응답 품질을 평가하는 전문가입니다.

사용자 쿼리: "{query}"
최종 응답 길이: {response_length}자
제안된 질문 수: {suggestion_count}개
포함된 상품 수: {product_count}개

최종 응답:
{final_response}

제안된 질문들:
{json.dumps(suggested_questions, ensure_ascii=False, indent=2)}

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


# 모든 평가자를 하나의 리스트로 정의
EVALUATORS = [
    WorkflowExecutionEvaluator(),
    SearchAccuracyEvaluator(), 
    DataExtractionEvaluator(),
    ResponseQualityEvaluator(),
    OverallPerformanceEvaluator()
]


def get_evaluators():
    """Get all evaluators for the shopping agent"""
    return EVALUATORS