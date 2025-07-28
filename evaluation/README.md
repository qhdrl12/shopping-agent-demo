# Shopping Agent Evaluation System

LangSmith 기반 무신사 쇼핑 에이전트 평가 시스템입니다. 데이터셋을 활용하여 에이전트를 체계적으로 평가하고 개선 과정을 추적할 수 있습니다.

## 🎯 주요 기능

- **자동화된 평가**: LangSmith 데이터셋을 순회하며 에이전트 추론 및 평가 수행
- **다중 메트릭**: 워크플로우 실행, 검색 정확도, 데이터 추출, 응답 품질, 전체 성능 등 5가지 평가 지표
- **실험 관리**: LangSmith Experiments에 결과 저장 및 비교 분석
- **트렌드 분석**: 시간에 따른 성능 변화 추적
- **상세 리포팅**: 개선점 도출을 위한 종합 분석 리포트

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  LangSmith      │    │  Evaluation     │    │  LangSmith      │
│  Datasets       │───▶│  Engine         │───▶│  Experiments    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │  Agent System   │
                       │  (LangGraph)    │
                       └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │  Evaluation     │
                       │  Metrics        │
                       └─────────────────┘
```

## 📊 평가 메트릭

### 1. Workflow Execution (20%)
- 쿼리 타입 분류 정확성
- 검색 쿼리 최적화 품질
- 도구 사용 효율성
- 오류 처리 및 복구

### 2. Search Accuracy (25%)
- 검색 결과 관련성
- 필터링 효과성
- 상품 링크 품질

### 3. Data Extraction (20%)
- 정보 완성도
- 데이터 정확성
- 구조화된 형식

### 4. Response Quality (25%)
- 추천 적절성
- 정보 유용성
- 응답 포괄성
- 실용적 실행가능성

### 5. Overall Performance (10%)
- 실행 속도
- 오류 처리
- 사용자 경험
- 시스템 신뢰성

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 평가 시스템 설치
./scripts/setup_evaluation.sh

# 환경 변수 설정 (.env 파일)
OPENAI_API_KEY=your_openai_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=musinsa-shopping-agent
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

### 2. 단일 쿼리 테스트

```bash
# 개별 쿼리 평가
python scripts/run_evaluation.py --mode single --query "나이키 운동화 추천해줘"
```

### 3. 전체 데이터셋 평가

```bash
# 전체 평가 실행
python scripts/run_evaluation.py --mode full --dataset shopping_agent_dataset

# 병렬 처리 (주의: 안정성을 위해 1-2로 제한 권장)
python scripts/run_evaluation.py --mode full --dataset shopping_agent_dataset --concurrency 1

# 샘플 크기 제한
python scripts/run_evaluation.py --mode full --dataset shopping_agent_dataset --sample-size 10
```

### 4. 실험 비교

```bash
# 두 실험 비교
python scripts/run_evaluation.py --mode compare --experiments exp1 exp2

# 트렌드 분석
python scripts/run_evaluation.py --mode trend --days 30
```

### 5. 상세 리포트 생성

```bash
# 리포트 생성
python scripts/run_evaluation.py --mode report --experiment experiment_name --output report.md
```

## 📚 사용 예시

### 기본 평가 워크플로우

```python
from evaluation.runner import ShoppingAgentRunner
from evaluation.analyzer import EvaluationAnalyzer

# 1. 평가 실행
runner = ShoppingAgentRunner()
experiment_id = runner.run_evaluation("shopping_agent_dataset")

# 2. 결과 분석
analyzer = EvaluationAnalyzer()
results = analyzer.get_experiment_results(experiment_id)

# 3. 리포트 생성
report = analyzer.generate_detailed_report(experiment_id)
print(report)
```

### 개선 추적

```python
from evaluation.analyzer import PerformanceTracker

tracker = PerformanceTracker()
improvements = tracker.track_improvements(
    baseline_experiment="baseline_exp",
    current_experiment="improved_exp"
)

print(f"Overall improvement: {improvements['overall_improvement']}")
print(f"Improved metrics: {improvements['improved_metrics']}")
```

## 🔧 고급 설정

### 평가 설정 커스터마이징

```python
# evaluation/config.py 파일에서 설정 변경
from evaluation.config import EvaluationConfig

config = EvaluationConfig()
config.evaluation_model = "gpt-4o-mini"  # 더 빠른 평가용
config.default_max_concurrency = 2      # 병렬 처리 증가
```

### 커스텀 평가자 추가

```python
from evaluation.evaluators import BaseEvaluator

class CustomEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__()
        self.name = "custom_metric"
        self.max_score = 100
    
    def evaluate(self, inputs, outputs, reference=None):
        # 커스텀 평가 로직
        return {
            "key": self.name,
            "score": 0.85,
            "comment": "Custom evaluation result"
        }
```

## 📁 디렉터리 구조

```
evaluation/
├── __init__.py              # 패키지 초기화
├── README.md               # 이 문서
├── config.py               # 설정 관리
├── evaluators.py           # 평가 함수들
├── runner.py               # 평가 실행 엔진
├── analyzer.py             # 결과 분석 도구
├── results/                # 평가 결과 저장
├── reports/                # 생성된 리포트
├── datasets/               # 로컬 데이터셋
└── templates/              # 리포트 템플릿

scripts/
├── run_evaluation.py       # 메인 실행 스크립트
├── setup_evaluation.sh     # 설치 스크립트
├── test_evaluation.py      # 테스트 스크립트
└── logs/                   # 실행 로그
```

## 🎛️ 명령어 레퍼런스

### run_evaluation.py 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--mode single` | 단일 쿼리 평가 | `--query "운동화 추천"` |
| `--mode full` | 전체 데이터셋 평가 | `--dataset dataset_name` |
| `--mode compare` | 실험 비교 | `--experiments exp1 exp2` |
| `--mode trend` | 트렌드 분석 | `--days 30` |
| `--mode report` | 리포트 생성 | `--experiment exp_name` |
| `--mode list-datasets` | 데이터셋 목록 | |
| `--mode create-sample` | 샘플 데이터셋 생성 | |

### 공통 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--concurrency N` | 최대 동시 실행 수 | 1 |
| `--sample-size N` | 평가할 예시 수 제한 | 전체 |
| `--verbose` | 상세 출력 | False |
| `--output FILE` | 출력 파일 지정 | stdout |

## 🔍 트러블슈팅

### 일반적인 문제들

#### 1. 환경 변수 오류
```bash
❌ Missing required environment variables: LANGSMITH_API_KEY
```
**해결**: `.env` 파일에 필수 환경 변수 설정

#### 2. 평가 실행 실패
```bash
❌ Evaluation failed: No dataset found
```
**해결**: LangSmith에 데이터셋이 존재하는지 확인
```bash
python scripts/run_evaluation.py --mode list-datasets
```

#### 3. 동시 실행 오류
```bash
❌ Rate limit exceeded
```
**해결**: `--concurrency 1`로 순차 실행

#### 4. 메모리 부족
**해결**: `--sample-size` 옵션으로 평가 크기 제한

### 성능 최적화

1. **평가 모델 선택**:
   - `gpt-4o`: 최고 품질 (느림, 비쌈)
   - `gpt-4o-mini`: 균형 (권장)

2. **병렬 처리**:
   - 안정성: `--concurrency 1`
   - 성능: `--concurrency 2-3` (주의)

3. **배치 크기**:
   - 테스트: `--sample-size 10`
   - 전체 평가: 샘플 크기 제한 없음

## 📈 개선 방법론

### 1. 기준선 설정
```bash
# 초기 평가 실행
python scripts/run_evaluation.py --mode full --dataset baseline_dataset --experiment baseline_v1
```

### 2. 변경 사항 적용 후 재평가
```bash
# 개선된 버전 평가
python scripts/run_evaluation.py --mode full --dataset baseline_dataset --experiment improved_v1
```

### 3. 성능 비교
```bash
# 개선 효과 분석
python scripts/run_evaluation.py --mode compare --experiments baseline_v1 improved_v1
```

### 4. 지속적 모니터링
```bash
# 주기적 트렌드 분석
python scripts/run_evaluation.py --mode trend --days 30
```

## 🤝 기여 가이드

평가 시스템 개선에 기여하려면:

1. **새로운 평가 메트릭 추가**: `evaluation/evaluators.py`에 새 클래스 구현
2. **분석 도구 확장**: `evaluation/analyzer.py`에 새 분석 함수 추가
3. **리포트 개선**: `evaluation/templates/` 디렉터리에 새 템플릿 추가

## 📞 지원

문제가 발생하거나 질문이 있으면:

1. **로그 확인**: `scripts/logs/evaluation.log`
2. **테스트 실행**: `python scripts/test_evaluation.py`
3. **설정 검증**: `python -c "from evaluation.config import validate_all_configs; print(validate_all_configs())"`

---

**개발팀**: Shopping Agent Team  
**업데이트**: 2024년 12월  
**버전**: 1.0.0