"""
Configuration settings for the evaluation system

Centralized configuration for evaluation parameters, thresholds, and settings.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class EvaluationConfig:
    """
    Main configuration class for evaluation settings
    """
    
    # Model Configuration
    evaluation_model: str = "gpt-4o"
    evaluation_temperature: float = 0.1
    
    # Performance Thresholds
    excellent_latency_general: float = 5.0      # seconds
    good_latency_general: float = 10.0
    acceptable_latency_general: float = 20.0
    
    excellent_latency_search: float = 15.0      # seconds  
    good_latency_search: float = 30.0
    acceptable_latency_search: float = 60.0
    
    # Scoring Thresholds
    low_performance_threshold: float = 0.5      # Below this is considered low performance
    significant_improvement_threshold: float = 0.01  # Minimum change to be significant
    trend_stable_threshold: float = 0.001       # Slope threshold for stable trends
    
    # Evaluation Parameters
    default_max_concurrency: int = 1           # Conservative default for stability
    default_evaluation_timeout: int = 300      # 5 minutes per evaluation
    
    # Metric Weights (for overall score calculation)
    metric_weights: Dict[str, float] = field(default_factory=lambda: {
        "workflow_execution": 0.20,
        "search_accuracy": 0.25,
        "data_extraction": 0.20, 
        "response_quality": 0.25,
        "overall_performance": 0.10
    })
    
    # Required Fields for Product Data
    required_product_fields: List[str] = field(default_factory=lambda: [
        "name", "price", "brand", "image_url", "product_url"
    ])
    
    optional_product_fields: List[str] = field(default_factory=lambda: [
        "description", "category", "color", "size", "rating", "reviews"
    ])
    
    # LangSmith Configuration
    langsmith_project: str = field(default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "musinsa-shopping-agent"))
    default_dataset_name: str = "shopping_agent_dataset"
    experiment_prefix: str = "shopping_agent_eval"
    
    # Report Configuration
    report_template_path: str = "evaluation/templates/report_template.md"
    max_error_examples: int = 5
    max_low_performance_examples: int = 5
    
    # Trend Analysis Configuration
    default_trend_days: int = 30
    min_experiments_for_trend: int = 3
    
    @classmethod
    def from_env(cls) -> 'EvaluationConfig':
        """
        Create configuration from environment variables
        """
        config = cls()
        
        # Override with environment variables if present
        if os.getenv("EVALUATION_MODEL"):
            config.evaluation_model = os.getenv("EVALUATION_MODEL")
        
        if os.getenv("EVALUATION_TEMPERATURE"):
            config.evaluation_temperature = float(os.getenv("EVALUATION_TEMPERATURE"))
        
        if os.getenv("MAX_CONCURRENCY"):
            config.default_max_concurrency = int(os.getenv("MAX_CONCURRENCY"))
        
        if os.getenv("EVALUATION_TIMEOUT"):
            config.default_evaluation_timeout = int(os.getenv("EVALUATION_TIMEOUT"))
        
        return config
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues
        """
        issues = []
        
        # Check weights sum to 1.0
        weight_sum = sum(self.metric_weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            issues.append(f"Metric weights sum to {weight_sum:.3f}, should be 1.0")
        
        # Check thresholds are logical
        if self.good_latency_general <= self.excellent_latency_general:
            issues.append("Good latency threshold should be greater than excellent threshold")
        
        if self.acceptable_latency_general <= self.good_latency_general:
            issues.append("Acceptable latency threshold should be greater than good threshold")
        
        # Check temperature is reasonable
        if not (0.0 <= self.evaluation_temperature <= 2.0):
            issues.append(f"Evaluation temperature {self.evaluation_temperature} should be between 0.0 and 2.0")
        
        return issues


@dataclass  
class DatasetConfig:
    """
    Configuration for dataset management
    """
    
    # Sample Dataset Examples
    sample_queries: List[str] = field(default_factory=lambda: [
        "나이키 운동화 추천해줘",
        "겨울 패딩 자켓 찾고 있어", 
        "20만원 이하 정장 추천",
        "캐주얼한 청바지 보여줘",
        "여성용 운동복 세트",
        "명품 가방 추천해줘",
        "학생용 백팩 찾아줘",
        "봄 원피스 추천",
        "남성 구두 추천해줘",
        "아디다스 후드티 찾고 있어",
        "여름 반팔 티셔츠",
        "비즈니스 캐주얼 셔츠",
        "운동화 끈 없는 거",
        "화이트 스니커즈",
        "검은색 코트",
        "따뜻한 목도리",
        "가죽 지갑 추천",
        "데님 재킷",
        "편안한 트레이닝복",
        "정장용 넥타이"
    ])
    
    # Dataset Categories for Organization
    categories: Dict[str, List[str]] = field(default_factory=lambda: {
        "clothing_upper": [
            "셔츠 추천해줘",
            "후드티 찾고 있어", 
            "코트 보여줘",
            "재킷 추천"
        ],
        "clothing_lower": [
            "청바지 추천",
            "정장 바지",
            "운동복 하의",
            "스커트 추천"
        ],
        "shoes": [
            "운동화 추천",
            "구두 찾아줘",
            "부츠 보여줘",
            "슬리퍼 추천"
        ],
        "accessories": [
            "가방 추천",
            "지갑 찾아줘", 
            "벨트 보여줘",
            "모자 추천"
        ],
        "seasonal": [
            "여름옷 추천",
            "겨울 패딩",
            "봄 원피스",
            "가을 자켓"
        ]
    })


@dataclass
class ReportConfig:
    """
    Configuration for report generation
    """
    
    # Report Sections
    include_executive_summary: bool = True
    include_detailed_metrics: bool = True
    include_performance_issues: bool = True
    include_recommendations: bool = True
    include_trend_analysis: bool = False
    
    # Report Formatting
    markdown_format: bool = True
    include_charts: bool = False  # Requires matplotlib
    max_chart_width: int = 800
    max_chart_height: int = 600
    
    # Content Limits
    max_error_details: int = 10
    max_recommendation_items: int = 5
    summary_text_length: int = 500
    
    # Output Options
    auto_timestamp: bool = True
    include_metadata: bool = True
    compress_large_reports: bool = True
    large_report_threshold: int = 100  # KB


# Global configuration instances
evaluation_config = EvaluationConfig.from_env()
dataset_config = DatasetConfig()
report_config = ReportConfig()


def get_evaluation_config() -> EvaluationConfig:
    """Get the global evaluation configuration"""
    return evaluation_config


def get_dataset_config() -> DatasetConfig:
    """Get the global dataset configuration"""
    return dataset_config


def get_report_config() -> ReportConfig:
    """Get the global report configuration"""
    return report_config


def validate_all_configs() -> Dict[str, List[str]]:
    """
    Validate all configurations and return any issues
    """
    return {
        "evaluation": evaluation_config.validate(),
        "dataset": [],  # DatasetConfig doesn't need validation currently
        "report": []    # ReportConfig doesn't need validation currently
    }