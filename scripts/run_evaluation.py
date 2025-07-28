#!/usr/bin/env python3
"""
Shopping Agent Evaluation Script

Main script for running comprehensive evaluations of the shopping agent.
Supports multiple modes of operation:
1. Single query evaluation (for testing)
2. Full dataset evaluation (for comprehensive assessment)
3. Comparison between experiments
4. Trend analysis over time

Usage Examples:
    # Test a single query
    python scripts/run_evaluation.py --mode single --query "나이키 운동화 추천해줘"
    
    # Run full evaluation on a dataset
    python scripts/run_evaluation.py --mode full --dataset shopping_agent_dataset
    
    # Compare two experiments
    python scripts/run_evaluation.py --mode compare --experiments exp1 exp2
    
    # Generate trend analysis
    python scripts/run_evaluation.py --mode trend --days 30
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from evaluation.runner import (
    ShoppingAgentRunner, 
    DatasetManager,
    run_evaluation,
    test_single_query,
    list_datasets
)
from evaluation.analyzer import (
    EvaluationAnalyzer,
    PerformanceTracker,
    analyze_experiment,
    compare_experiments,
    generate_report
)


def setup_environment():
    """
    Validate environment setup and requirements
    """
    required_env_vars = [
        "OPENAI_API_KEY",
        "LANGSMITH_API_KEY", 
        "LANGSMITH_PROJECT",
        "FIRECRAWL_API_KEY"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment")
        return False
    
    # Enable LangSmith tracing
    os.environ["LANGSMITH_TRACING"] = "true"
    
    print("✅ Environment setup complete")
    return True


def run_single_query_to_langsmith(query: str, verbose: bool = True) -> None:
    """
    Run evaluation on a single query and save to LangSmith
    """
    print(f"\n🔍 Single Query Evaluation (LangSmith)")
    print(f"Query: '{query}'")
    print("=" * 60)
    
    try:
        # Create a temporary dataset with this single query
        manager = DatasetManager()
        temp_dataset_name = f"temp_single_query_{int(time.time())}"
        
        dataset_id = manager.create_sample_dataset(
            dataset_name=temp_dataset_name,
            examples=[{"query": query}],
            description=f"Temporary dataset for single query evaluation: '{query}'"
        )
        
        print(f"📋 Created temporary dataset: {temp_dataset_name}")
        
        # Run evaluation
        import asyncio
        experiment_id = asyncio.run(run_evaluation(
            dataset_name=temp_dataset_name,
            experiment_name=f"single_query_eval_{int(time.time())}",
            max_concurrency=1,
            sample_size=1
        ))
        
        print(f"\n✅ Evaluation completed and saved to LangSmith!")
        print(f"🔗 Experiment: {experiment_id}")
        print(f"📊 Check results at: https://smith.langchain.com/")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")


def run_single_query_evaluation(query: str, verbose: bool = True) -> None:
    """
    Run evaluation on a single query for testing
    """
    print(f"\n🔍 Single Query Evaluation")
    print(f"Query: '{query}'")
    print("=" * 60)
    
    try:
        result = test_single_query(query, verbose=verbose)
        if result["agent_result"]["success"]:
            print(f"\n✅ Evaluation completed successfully!")
            print(f"Overall Score: {result['overall_score']:.3f}")
        else:
            print(f"\n❌ Agent execution failed: {result['agent_result']['error']}")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")


def run_full_evaluation(dataset_name: str, 
                       experiment_name: Optional[str] = None,
                       max_concurrency: int = 1,
                       sample_size: Optional[int] = None) -> None:
    """
    Run full evaluation on a LangSmith dataset
    """
    print(f"\n📊 Full Dataset Evaluation")
    print(f"Dataset: {dataset_name}")
    if experiment_name:
        print(f"Experiment: {experiment_name}")
    print(f"Max Concurrency: {max_concurrency}")
    if sample_size:
        print(f"Sample Size: {sample_size}")
    print("=" * 60)
    
    try:
        import asyncio
        experiment_id = asyncio.run(run_evaluation(
            dataset_name=dataset_name,
            experiment_name=experiment_name,
            max_concurrency=max_concurrency,
            sample_size=sample_size
        ))
        
        print(f"\n✅ Evaluation completed!")
        print(f"Experiment ID: {experiment_id}")
        
        # Generate and display a quick summary
        analyzer = EvaluationAnalyzer()
        results = analyzer.get_experiment_results(experiment_id)
        
        if results["metrics_summary"]:
            print(f"\n📈 Quick Summary:")
            for metric, stats in results["metrics_summary"].items():
                print(f"  {metric}: {stats['mean']:.3f} ± {stats['std']:.3f}")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")


def run_comparison(experiment_names: List[str]) -> None:
    """
    Compare multiple experiments
    """
    print(f"\n🔄 Experiment Comparison")
    print(f"Experiments: {', '.join(experiment_names)}")
    print("=" * 60)
    
    try:
        comparison = compare_experiments(experiment_names)
        
        print(f"\n📊 Comparison Results:")
        
        # Show metrics comparison
        if comparison["metrics_comparison"]:
            print(f"\nMetric Performance:")
            for metric in ["workflow_execution", "search_accuracy", "data_extraction", 
                          "response_quality", "overall_performance"]:
                if metric in comparison["metrics_comparison"]:
                    scores = comparison["metrics_comparison"][metric]
                    print(f"  {metric}:")
                    for exp_name, score in scores.items():
                        print(f"    {exp_name}: {score:.3f}")
        
        # Show improvements and regressions
        if comparison["improvements"]:
            print(f"\n✅ Improvements:")
            for metric, data in comparison["improvements"].items():
                print(f"  {metric}: {data['change']:+.3f} ({data['change_percent']:+.1f}%)")
        
        if comparison["regressions"]:
            print(f"\n❌ Regressions:")
            for metric, data in comparison["regressions"].items():
                print(f"  {metric}: {data['change']:+.3f} ({data['change_percent']:+.1f}%)")
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")


def run_trend_analysis(days_back: int = 30, experiment_prefix: str = "shopping_agent_eval") -> None:
    """
    Analyze trends over time
    """
    print(f"\n📈 Trend Analysis")
    print(f"Time Period: Last {days_back} days")
    print(f"Experiment Prefix: {experiment_prefix}")
    print("=" * 60)
    
    try:
        analyzer = EvaluationAnalyzer()
        trend_data = analyzer.generate_trend_analysis(
            experiment_prefix=experiment_prefix,
            days_back=days_back
        )
        
        print(f"\n📊 Trend Results:")
        print(f"Experiments Found: {trend_data['experiment_count']}")
        
        if trend_data["date_range"]["start"]:
            print(f"Date Range: {trend_data['date_range']['start'].strftime('%Y-%m-%d')} to {trend_data['date_range']['end'].strftime('%Y-%m-%d')}")
        
        if trend_data["trend_analysis"]:
            print(f"\nTrend Analysis:")
            for metric, analysis in trend_data["trend_analysis"].items():
                direction_emoji = "📈" if analysis["direction"] == "improving" else "📉" if analysis["direction"] == "declining" else "➡️"
                print(f"  {direction_emoji} {metric}: {analysis['direction']} (slope: {analysis['slope']:+.4f})")
                print(f"     Latest: {analysis['latest_score']:.3f}, Best: {analysis['best_score']:.3f}, Worst: {analysis['worst_score']:.3f}")
        
    except Exception as e:
        print(f"❌ Trend analysis failed: {e}")


def generate_detailed_report(experiment_name: str, output_file: Optional[str] = None) -> None:
    """
    Generate a detailed evaluation report
    """
    print(f"\n📋 Generating Detailed Report")
    print(f"Experiment: {experiment_name}")
    if output_file:
        print(f"Output File: {output_file}")
    print("=" * 60)
    
    try:
        report = generate_report(experiment_name, output_file)
        
        if not output_file:
            print(report)
        
        print(f"\n✅ Report generated successfully!")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")


def list_available_datasets() -> None:
    """
    List all available datasets
    """
    print(f"\n📚 Available Datasets")
    print("=" * 60)
    
    try:
        datasets = list_datasets()
        
        if not datasets:
            print("No datasets found")
            return
        
        for dataset in datasets:
            print(f"📋 {dataset['name']}")
            print(f"   Examples: {dataset['example_count']}")
            if dataset['description']:
                print(f"   Description: {dataset['description']}")
            print(f"   Created: {dataset['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
    except Exception as e:
        print(f"❌ Failed to list datasets: {e}")


def create_sample_dataset() -> None:
    """
    Create a sample dataset for testing
    """
    print(f"\n🏗️  Creating Sample Dataset")
    print("=" * 60)
    
    sample_examples = [
        {"query": "나이키 운동화 추천해줘"},
        {"query": "겨울 패딩 자켓 찾고 있어"},
        {"query": "20만원 이하 정장 추천"},
        {"query": "캐주얼한 청바지 보여줘"},
        {"query": "여성용 운동복 세트"},
        {"query": "명품 가방 추천해줘"},
        {"query": "학생용 백팩 찾아줘"},
        {"query": "봄 원피스 추천"},
        {"query": "남성 구두 추천해줘"},
        {"query": "아디다스 후드티 찾고 있어"}
    ]
    
    try:
        manager = DatasetManager()
        dataset_id = manager.create_sample_dataset(
            dataset_name="shopping_agent_sample_dataset",
            examples=sample_examples,
            description="Sample dataset for testing shopping agent evaluation"
        )
        
        print(f"✅ Sample dataset created with ID: {dataset_id}")
        
    except Exception as e:
        print(f"❌ Failed to create sample dataset: {e}")


def main():
    """
    Main function to handle command line arguments and execute the appropriate action
    """
    parser = argparse.ArgumentParser(
        description="Shopping Agent Evaluation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test single query (local only)
    python scripts/run_evaluation.py --mode single --query "나이키 운동화 추천해줘"
    
    # Test single query and save to LangSmith
    python scripts/run_evaluation.py --mode single-to-langsmith --query "나이키 운동화 추천해줘"
    
    # Run full evaluation
    python scripts/run_evaluation.py --mode full --dataset shopping_agent_dataset
    
    # Compare experiments
    python scripts/run_evaluation.py --mode compare --experiments exp1 exp2
    
    # Trend analysis
    python scripts/run_evaluation.py --mode trend --days 30
    
    # Generate report
    python scripts/run_evaluation.py --mode report --experiment exp_name --output report.md
    
    # List datasets
    python scripts/run_evaluation.py --mode list-datasets
    
    # Create sample dataset
    python scripts/run_evaluation.py --mode create-sample
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["single", "single-to-langsmith", "full", "compare", "trend", "report", "list-datasets", "create-sample"],
        required=True,
        help="Evaluation mode"
    )
    
    # Single query mode
    parser.add_argument("--query", help="Query for single evaluation mode")
    
    # Full evaluation mode
    parser.add_argument("--dataset", help="Dataset name for full evaluation")
    parser.add_argument("--experiment", help="Experiment name (optional)")
    parser.add_argument("--concurrency", type=int, default=1, help="Max concurrency for evaluation")
    parser.add_argument("--sample-size", type=int, help="Limit number of examples to evaluate")
    
    # Comparison mode
    parser.add_argument("--experiments", nargs="+", help="Experiment names to compare")
    
    # Trend analysis mode
    parser.add_argument("--days", type=int, default=30, help="Days back for trend analysis")
    parser.add_argument("--prefix", default="shopping_agent_eval", help="Experiment prefix for trend analysis")
    
    # Report mode
    parser.add_argument("--output", help="Output file for report")
    
    # General options
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-env-check", action="store_true", help="Skip environment validation")
    
    args = parser.parse_args()
    
    # Setup environment
    if not args.no_env_check and not setup_environment():
        sys.exit(1)
    
    # Execute based on mode
    try:
        if args.mode == "single":
            if not args.query:
                parser.error("--query is required for single mode")
            run_single_query_evaluation(args.query, args.verbose)
            
        elif args.mode == "single-to-langsmith":
            if not args.query:
                parser.error("--query is required for single-to-langsmith mode")
            run_single_query_to_langsmith(args.query, args.verbose)
            
        elif args.mode == "full":
            if not args.dataset:
                parser.error("--dataset is required for full mode")
            run_full_evaluation(
                dataset_name=args.dataset,
                experiment_name=args.experiment,
                max_concurrency=args.concurrency,
                sample_size=args.sample_size
            )
            
        elif args.mode == "compare":
            if not args.experiments or len(args.experiments) < 2:
                parser.error("At least 2 experiment names are required for compare mode")
            run_comparison(args.experiments)
            
        elif args.mode == "trend":
            run_trend_analysis(args.days, args.prefix)
            
        elif args.mode == "report":
            if not args.experiment:
                parser.error("--experiment is required for report mode")
            generate_detailed_report(args.experiment, args.output)
            
        elif args.mode == "list-datasets":
            list_available_datasets()
            
        elif args.mode == "create-sample":
            create_sample_dataset()
    
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()