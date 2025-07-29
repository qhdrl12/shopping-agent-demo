"""
Inference-Only Execution System

추론만 실행하고 결과를 캐시에 저장하는 시스템:
- 데이터셋별 추론 실행 및 캐시 저장
- 진행률 추적 및 중단/재개 지원
- 실패한 예제 재시도 로직
- 메모리 효율적인 스트리밍 처리
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from langsmith import Client

from evaluation.cache_manager import cache_manager
from evaluation.runner import ShoppingAgentRunner


class InferenceRunner:
    """추론 전용 실행기"""
    
    def __init__(self, langsmith_client: Optional[Client] = None):
        self.client = langsmith_client or Client()
        self.agent_runner = ShoppingAgentRunner(langsmith_client=self.client)
        self.cache = cache_manager
    
    async def run_inference_only(self, 
                                dataset_name: str,
                                max_concurrency: int = 1,
                                sample_size: Optional[int] = None,
                                resume: bool = True) -> Dict[str, Any]:
        """
        추론만 실행하고 결과를 캐시에 저장
        
        Args:
            dataset_name: LangSmith 데이터셋 이름
            max_concurrency: 최대 동시 실행 수
            sample_size: 처리할 예제 수 제한 (None이면 전체)
            resume: 기존 캐시된 결과 재사용 여부
            
        Returns:
            실행 결과 통계
        """
        
        print(f"🔍 Starting inference-only mode for dataset: {dataset_name}")
        print(f"⚙️ Max concurrency: {max_concurrency}")
        if sample_size:
            print(f"🔢 Sample size: {sample_size}")
        print(f"🔄 Resume mode: {resume}")
        print("=" * 60)
        
        # 데이터셋 로드
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            print(f"✅ Dataset loaded: {dataset.name} ({dataset.example_count} examples)")
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            raise
        
        # 캐시 상태 확인
        cache_status = self.cache.get_dataset_cache_status(dataset_name)
        print(f"\n📊 Cache Status:")
        print(f"  Cached examples: {cache_status['completed_examples']}/{cache_status['total_examples']}")
        print(f"  Completion rate: {cache_status['completion_rate']:.1%}")
        print(f"  Version match: {cache_status['version_match']}")
        
        if not cache_status['version_match'] and cache_status['cached']:
            print(f"⚠️ Agent version mismatch detected. Cache will be rebuilt.")
            resume = False
        
        # 처리할 예제들 수집
        examples = list(self.client.list_examples(
            dataset_id=dataset.id, 
            limit=sample_size
        ))
        
        if resume:
            # 이미 캐시된 예제들 제외
            cached_ids = set(self.cache.get_cached_example_ids(dataset_name))
            examples_to_process = [ex for ex in examples if str(ex.id) not in cached_ids]
            print(f"🔄 Resume mode: {len(examples_to_process)} examples to process")
        else:
            examples_to_process = examples
            print(f"🆕 Fresh start: {len(examples_to_process)} examples to process")
        
        if not examples_to_process:
            print("✅ All examples already cached and up to date!")
            return {
                "dataset_name": dataset_name,
                "total_examples": len(examples),
                "processed_examples": 0,
                "cached_examples": len(examples),
                "failed_examples": 0,
                "execution_time": 0.0,
                "status": "already_complete"
            }
        
        # 추론 실행
        start_time = time.time()
        results = await self._process_examples_batch(
            dataset_name, 
            examples_to_process, 
            max_concurrency
        )
        execution_time = time.time() - start_time
        
        # 결과 요약
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        print(f"\n🎉 Inference completed!")
        print(f"📊 Results Summary:")
        print(f"  Total processed: {len(results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Success rate: {successful/len(results):.1%}")
        print(f"  Execution time: {execution_time:.1f}s")
        print(f"  Average time per example: {execution_time/len(results):.1f}s")
        
        # 캐시 상태 업데이트
        final_cache_status = self.cache.get_dataset_cache_status(dataset_name)
        print(f"\n📈 Final Cache Status:")
        print(f"  Total cached: {final_cache_status['completed_examples']}")
        print(f"  Completion rate: {final_cache_status['completion_rate']:.1%}")
        
        return {
            "dataset_name": dataset_name,
            "total_examples": len(examples),
            "processed_examples": len(results),
            "successful_examples": successful,
            "failed_examples": failed,
            "success_rate": successful / len(results) if results else 0.0,
            "execution_time": execution_time,
            "avg_time_per_example": execution_time / len(results) if results else 0.0,
            "cache_completion_rate": final_cache_status["completion_rate"],
            "status": "completed"
        }
    
    async def _process_examples_batch(self, 
                                    dataset_name: str,
                                    examples: List[Any],
                                    max_concurrency: int) -> List[Dict[str, Any]]:
        """예제들을 배치로 처리"""
        
        # 세마포어로 동시 실행 수 제한
        semaphore = asyncio.Semaphore(max_concurrency)
        
        # 모든 예제에 대한 태스크 생성
        tasks = []
        for i, example in enumerate(examples):
            task = self._process_single_example_with_semaphore(
                semaphore, dataset_name, example, i + 1, len(examples)
            )
            tasks.append(task)
        
        # 모든 태스크 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Example {i+1} failed with exception: {result}")
                processed_results.append({
                    "example_id": examples[i].id,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_example_with_semaphore(self,
                                                   semaphore: asyncio.Semaphore,
                                                   dataset_name: str,
                                                   example: Any,
                                                   current: int,
                                                   total: int) -> Dict[str, Any]:
        """세마포어를 사용한 단일 예제 처리"""
        async with semaphore:
            return await self._process_single_example(dataset_name, example, current, total)
    
    async def _process_single_example(self,
                                    dataset_name: str,
                                    example: Any,
                                    current: int,
                                    total: int) -> Dict[str, Any]:
        """단일 예제 추론 실행"""
        
        example_id = str(example.id)  # UUID를 문자열로 변환
        inputs = example.inputs if hasattr(example, 'inputs') else {}
        
        print(f"🔄 Processing example {current}/{total}: {example_id}")
        
        try:
            # 쿼리 추출 (여러 필드명 시도)
            query = (inputs.get("query") or 
                    inputs.get("input") or 
                    inputs.get("question") or 
                    inputs.get("text") or
                    inputs.get("prompt") or
                    "")
            
            # 단일 값 딕셔너리 처리
            if not query and len(inputs) == 1:
                query = list(inputs.values())[0]
            
            if not query:
                raise ValueError(f"No query found in inputs: {list(inputs.keys())}")
            
            # 에이전트 실행
            start_time = time.time()
            result = await self.agent_runner.run_agent(query)
            inference_time = time.time() - start_time
            
            if result.get("success", False):
                # 캐시에 저장
                cache_success = self.cache.save_inference_result(
                    dataset_name, example_id, result
                )
                
                if cache_success:
                    print(f"✅ Example {current}/{total} completed and cached ({inference_time:.1f}s)")
                    return {
                        "example_id": example_id,
                        "success": True,
                        "inference_time": inference_time,
                        "cached": True
                    }
                else:
                    print(f"⚠️ Example {current}/{total} completed but cache failed")
                    return {
                        "example_id": example_id,
                        "success": True,
                        "inference_time": inference_time,
                        "cached": False,
                        "cache_error": "Failed to save to cache"
                    }
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"❌ Example {current}/{total} failed: {error_msg}")
                return {
                    "example_id": example_id,
                    "success": False,
                    "error": error_msg,
                    "inference_time": inference_time
                }
                
        except Exception as e:
            print(f"❌ Example {current}/{total} exception: {e}")
            return {
                "example_id": example_id,
                "success": False,
                "error": str(e),
                "inference_time": 0.0
            }
    
    def get_inference_progress(self, dataset_name: str) -> Dict[str, Any]:
        """추론 진행률 조회"""
        cache_status = self.cache.get_dataset_cache_status(dataset_name)
        
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            total_examples = dataset.example_count
        except Exception:
            total_examples = cache_status.get("total_examples", 0)
        
        return {
            "dataset_name": dataset_name,
            "total_examples": total_examples,
            "completed_examples": cache_status["completed_examples"],
            "progress_percentage": cache_status["completion_rate"] * 100,
            "agent_version": cache_status["agent_version"],
            "version_match": cache_status["version_match"],
            "last_updated": cache_status.get("last_updated")
        }


# 편의 함수들
async def run_inference_only(dataset_name: str,
                           max_concurrency: int = 1,
                           sample_size: Optional[int] = None,
                           resume: bool = True) -> Dict[str, Any]:
    """추론 전용 실행 편의 함수"""
    runner = InferenceRunner()
    return await runner.run_inference_only(
        dataset_name=dataset_name,
        max_concurrency=max_concurrency,
        sample_size=sample_size,
        resume=resume
    )


def get_inference_progress(dataset_name: str) -> Dict[str, Any]:
    """추론 진행률 조회 편의 함수"""
    runner = InferenceRunner()
    return runner.get_inference_progress(dataset_name)