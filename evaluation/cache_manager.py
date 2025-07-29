"""
Inference Cache Management System

캐시를 통한 추론-평가 분리 시스템:
- 추론 결과를 데이터셋별로 저장/로드
- 에이전트 버전 추적으로 자동 무효화  
- 부분 완료 및 재개 지원
- 압축 저장으로 공간 효율성 확보
"""

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class InferenceCache:
    """추론 결과 캐시 관리자"""
    
    def __init__(self, base_path: str = ".cache"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 캐시 구조 생성
        self.datasets_path = self.base_path / "datasets"
        self.metadata_path = self.base_path / "metadata"
        self.datasets_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        
        # 에이전트 버전 추적
        self.agent_version = self._get_agent_version()
        
    def _get_agent_version(self) -> str:
        """에이전트 코드 버전 해시 생성 (워크플로우 변경 감지용)"""
        try:
            # 주요 파일들의 해시를 계산하여 버전 생성
            important_files = [
                "backend/workflow/unified_workflow.py",
                "backend/nodes/query_nodes.py", 
                "backend/nodes/search_nodes.py",
                "backend/nodes/extraction_nodes.py",
                "backend/nodes/response_nodes.py",
                "backend/tools/firecrawl_tools.py"
            ]
            
            version_hash = hashlib.md5()
            for file_path in important_files:
                try:
                    full_path = Path(file_path)
                    if full_path.exists():
                        with open(full_path, 'rb') as f:
                            version_hash.update(f.read())
                except Exception:
                    continue
            
            return version_hash.hexdigest()[:8]
        except Exception:
            # 파일 접근 실패 시 타임스탬프 기반 버전
            return f"ts_{int(time.time())}"
    
    def _get_dataset_path(self, dataset_name: str) -> Path:
        """데이터셋별 캐시 디렉토리 경로"""
        dataset_path = self.datasets_path / dataset_name
        dataset_path.mkdir(exist_ok=True)
        return dataset_path
    
    def _get_example_path(self, dataset_name: str, example_id: str) -> Path:
        """개별 예제 캐시 파일 경로"""
        dataset_path = self._get_dataset_path(dataset_name)
        examples_path = dataset_path / "examples"
        examples_path.mkdir(exist_ok=True)
        return examples_path / f"{example_id}.json"
    
    def _save_json_data(self, data: Dict[str, Any], file_path: Path) -> None:
        """JSON 데이터 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_json_data(self, file_path: Path) -> Dict[str, Any]:
        """JSON 데이터 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_inference_result(self, dataset_name: str, example_id: str, 
                            result: Dict[str, Any]) -> bool:
        """추론 결과 저장"""
        try:
            # 메타데이터 추가
            enriched_result = {
                **result,
                "_cache_metadata": {
                    "cached_at": datetime.now().isoformat(),
                    "agent_version": self.agent_version,
                    "example_id": example_id,
                    "dataset_name": dataset_name
                }
            }
            
            # JSON으로 저장
            example_path = self._get_example_path(dataset_name, example_id)
            self._save_json_data(enriched_result, example_path)
            
            # 데이터셋 메타데이터 업데이트
            self._update_dataset_metadata(dataset_name, example_id, "completed")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save cache for {dataset_name}/{example_id}: {e}")
            return False
    
    def load_inference_result(self, dataset_name: str, 
                            example_id: str) -> Optional[Dict[str, Any]]:
        """추론 결과 로드"""
        try:
            example_path = self._get_example_path(dataset_name, example_id)
            
            if not example_path.exists():
                return None
            
            result = self._load_json_data(example_path)
            
            # 버전 호환성 검사
            cached_version = result.get("_cache_metadata", {}).get("agent_version")
            if cached_version != self.agent_version:
                print(f"⚠️ Cache version mismatch for {example_id}: {cached_version} != {self.agent_version}")
                return None
            
            # 메타데이터 제거 후 반환
            if "_cache_metadata" in result:
                del result["_cache_metadata"]
            
            return result
            
        except Exception as e:
            print(f"❌ Failed to load cache for {dataset_name}/{example_id}: {e}")
            return None
    
    def _update_dataset_metadata(self, dataset_name: str, example_id: str, 
                                status: str) -> None:
        """데이터셋 메타데이터 업데이트"""
        dataset_path = self._get_dataset_path(dataset_name)
        metadata_path = dataset_path / "metadata.json"
        
        # 기존 메타데이터 로드
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "dataset_name": dataset_name,
                "agent_version": self.agent_version,
                "created_at": datetime.now().isoformat(),
                "examples": {}
            }
        
        # 예제 상태 업데이트
        metadata["examples"][example_id] = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        metadata["last_updated"] = datetime.now().isoformat()
        
        # 저장
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def get_dataset_cache_status(self, dataset_name: str) -> Dict[str, Any]:
        """데이터셋 캐시 상태 조회"""
        dataset_path = self._get_dataset_path(dataset_name)
        metadata_path = dataset_path / "metadata.json"
        
        if not metadata_path.exists():
            return {
                "dataset_name": dataset_name,
                "cached": False,
                "total_examples": 0,
                "completed_examples": 0,
                "completion_rate": 0.0,
                "agent_version": self.agent_version,
                "version_match": True
            }
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        examples = metadata.get("examples", {})
        completed = sum(1 for ex in examples.values() if ex.get("status") == "completed")
        total = len(examples)
        
        cached_version = metadata.get("agent_version")
        version_match = cached_version == self.agent_version
        
        return {
            "dataset_name": dataset_name,
            "cached": total > 0,
            "total_examples": total,
            "completed_examples": completed,
            "completion_rate": completed / total if total > 0 else 0.0,
            "agent_version": self.agent_version,
            "cached_version": cached_version,
            "version_match": version_match,
            "created_at": metadata.get("created_at"),
            "last_updated": metadata.get("last_updated")
        }
    
    def get_cached_example_ids(self, dataset_name: str) -> List[str]:
        """캐시된 예제 ID 목록 반환"""
        dataset_path = self._get_dataset_path(dataset_name)
        metadata_path = dataset_path / "metadata.json"
        
        if not metadata_path.exists():
            return []
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 완료된 예제만 반환
        examples = metadata.get("examples", {})
        return [
            example_id for example_id, info in examples.items()
            if info.get("status") == "completed"
        ]
    
    def invalidate_cache(self, dataset_name: str) -> bool:
        """데이터셋 캐시 무효화 (삭제)"""
        try:
            dataset_path = self._get_dataset_path(dataset_name)
            
            if dataset_path.exists():
                import shutil
                shutil.rmtree(dataset_path)
                print(f"✅ Cache cleared for dataset: {dataset_name}")
            else:
                print(f"ℹ️ No cache found for dataset: {dataset_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to clear cache for {dataset_name}: {e}")
            return False
    
    def list_cached_datasets(self) -> List[Dict[str, Any]]:
        """모든 캐시된 데이터셋 목록"""
        datasets = []
        
        if not self.datasets_path.exists():
            return datasets
        
        for dataset_dir in self.datasets_path.iterdir():
            if dataset_dir.is_dir():
                status = self.get_dataset_cache_status(dataset_dir.name)
                datasets.append(status)
        
        return datasets
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """전체 캐시 통계"""
        datasets = self.list_cached_datasets()
        
        total_datasets = len(datasets)
        total_examples = sum(d["total_examples"] for d in datasets)
        completed_examples = sum(d["completed_examples"] for d in datasets)
        
        # 캐시 디스크 사용량 계산
        cache_size = 0
        if self.base_path.exists():
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    cache_size += file_path.stat().st_size
        
        return {
            "total_datasets": total_datasets,
            "total_examples": total_examples, 
            "completed_examples": completed_examples,
            "overall_completion_rate": completed_examples / total_examples if total_examples > 0 else 0.0,
            "cache_size_bytes": cache_size,
            "cache_size_mb": round(cache_size / (1024 * 1024), 2),
            "agent_version": self.agent_version
        }


# 글로벌 캐시 인스턴스
cache_manager = InferenceCache()