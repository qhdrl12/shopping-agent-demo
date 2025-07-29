"""
Simple Evaluation-Only Execution System

캐시된 추론 결과로 평가만 실행하는 간단한 시스템
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
from langsmith import Client
from langsmith.evaluation import aevaluate

from evaluation.cache_manager import cache_manager
from evaluation.evaluators import get_parallel_evaluators


class EvaluationRunner:
    """평가 실행기"""
    
    def __init__(self, langsmith_client: Optional[Client] = None):
        self.client = langsmith_client or Client()
        self.cache = cache_manager
        self.evaluators = get_parallel_evaluators()  # 기본적으로 병렬 평가자 사용
    
    async def run_evaluation_only(self,
                                dataset_name: str,
                                experiment_name: Optional[str] = None,
                                max_concurrency: int = 3) -> str:
        """
        캐시된 결과로 평가만 실행 (간단한 버전)
        """
        
        print(f"⚡ Starting evaluation-only mode for dataset: {dataset_name}")
        print("=" * 60)
        
        # 실험 이름 생성
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"eval_only_{dataset_name}_{timestamp}"
        
        print(f"🚀 Starting cached evaluation...")
        start_time = time.time()
        
        try:
            # 간단한 방법: 캐시된 데이터를 직접 평가
            # LangSmith 데이터셋 로드
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            examples = list(self.client.list_examples(dataset_id=dataset.id))
            
            print(f"📊 Found {len(examples)} examples in dataset")
            
            # 각 예제에 대해 캐시된 결과로 평가 실행
            evaluation_results = []
            
            for example in examples:
                example_id = str(example.id)
                inputs = example.inputs if hasattr(example, 'inputs') else {}
                
                # 캐시에서 결과 로드
                cached_result = self.cache.load_inference_result(dataset_name, example_id)
                
                if cached_result is None:
                    print(f"⚠️ No cached result for example {example_id}, skipping...")
                    continue
                
                # 병렬 평가 실행
                print(f"🚀 Running parallel evaluation for example {example_id}...")
                parallel_results = await self.evaluators.evaluate_parallel(inputs, cached_result)
                
                for eval_result in parallel_results:
                    evaluation_results.append({
                        "example_id": example_id,
                        "evaluator": eval_result["key"],
                        "result": eval_result
                    })
            
            print(f"\n🎉 Direct evaluation completed!")
            print(f"📊 Processed: {len(evaluation_results)} evaluations")
            
            evaluation_time = time.time() - start_time
            print(f"⏱️  Evaluation time: {evaluation_time:.1f}s")
            
            return f"direct_eval_{experiment_name}"
            
        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            raise
    
    def _create_cached_target_function(self, dataset_name: str):
        """간단한 캐시 기반 target function"""
        
        def cached_target_function(inputs: Dict[str, Any]) -> Dict[str, Any]:
            # 다양한 방법으로 예제 ID 찾기
            example_id = None
            
            print(f"cached_target_function input : {inputs}")
            # 방법 1: inputs에서 직접
            if "example_id" in inputs:
                example_id = inputs["example_id"]
            
            # 방법 2: LangSmith 내부 구조 (실행해보면서 확인 필요)
            # 실제로는 LangSmith가 어떻게 example_id를 전달하는지 확인 후 수정
            
            if not example_id:
                # 임시: 쿼리 기반으로 찾기 (비효율적이지만 작동)
                query = (inputs.get("query") or 
                        inputs.get("input") or 
                        list(inputs.values())[0] if inputs else "")
                
                # 캐시에서 쿼리 매칭으로 찾기 (임시 방법)
                cached_examples = self.cache.get_cached_example_ids(dataset_name)
                print(f"cached_examples: {cached_examples}")
                for ex_id in cached_examples:
                    cached_result = self.cache.load_inference_result(dataset_name, ex_id)
                    if cached_result and cached_result.get("query") == query:
                        example_id = ex_id
                        break
            
            if not example_id:
                raise ValueError(f"Cannot find cached result for inputs: {list(inputs.keys())}")
            
            # 캐시에서 결과 로드
            cached_result = self.cache.load_inference_result(dataset_name, example_id)
            
            if cached_result is None:
                raise ValueError(f"No cached result found for example: {example_id}")
            
            # LangSmith 형식으로 반환
            return {
                "output": cached_result.get("final_response", ""),
                **cached_result  # 모든 평가 데이터 포함
            }
        
        return cached_target_function


# 편의 함수
async def run_evaluation_only(dataset_name: str,
                            experiment_name: Optional[str] = None,
                            max_concurrency: int = 3) -> str:
    """평가 전용 실행 편의 함수"""
    runner = EvaluationRunner()
    return await runner.run_evaluation_only(
        dataset_name=dataset_name,
        experiment_name=experiment_name,
        max_concurrency=max_concurrency
    )