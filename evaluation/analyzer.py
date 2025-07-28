"""
Evaluation Result Analysis and Reporting

Provides tools for analyzing evaluation results and generating reports:
1. Compare experiments across different agent versions
2. Generate performance trend analysis
3. Create detailed evaluation reports
4. Identify improvement opportunities
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from langsmith import Client
import pandas as pd
from pathlib import Path


class EvaluationAnalyzer:
    """
    Analyzes evaluation results and generates insights
    """
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or Client()
        self.metrics = [
            "workflow_execution",
            "search_accuracy", 
            "data_extraction",
            "response_quality",
            "overall_performance"
        ]
    
    def get_experiment_results(self, experiment_name: str) -> Dict[str, Any]:
        """
        Retrieve detailed results from a specific experiment
        """
        try:
            # Get the experiment
            experiments = list(self.client.list_sessions(
                reference_example_type="dataset",
                name=experiment_name
            ))
            
            if not experiments:
                raise ValueError(f"Experiment '{experiment_name}' not found")
            
            experiment = experiments[0]
            
            # Get all runs in the experiment
            runs = list(self.client.list_runs(session_id=experiment.id))
            
            results = {
                "experiment_name": experiment_name,
                "experiment_id": experiment.id,
                "run_count": len(runs),
                "created_at": experiment.start_time,
                "runs": [],
                "metrics_summary": {}
            }
            
            # Process each run
            metric_scores = {metric: [] for metric in self.metrics}
            
            for run in runs:
                run_data = {
                    "run_id": run.id,
                    "inputs": run.inputs,
                    "outputs": run.outputs,
                    "execution_time": (run.end_time - run.start_time).total_seconds() if run.end_time else None,
                    "error": run.error,
                    "feedback": {}
                }
                
                # Get feedback/evaluation results for this run
                feedback = list(self.client.list_feedback(run_ids=[run.id]))
                for fb in feedback:
                    run_data["feedback"][fb.key] = {
                        "score": fb.score,
                        "comment": fb.comment,
                        "metadata": fb.metadata
                    }
                    
                    # Collect scores for summary
                    if fb.key in metric_scores and fb.score is not None:
                        metric_scores[fb.key].append(fb.score)
                
                results["runs"].append(run_data)
            
            # Calculate summary statistics
            for metric, scores in metric_scores.items():
                if scores:
                    results["metrics_summary"][metric] = {
                        "mean": statistics.mean(scores),
                        "median": statistics.median(scores),
                        "min": min(scores),
                        "max": max(scores),
                        "std": statistics.stdev(scores) if len(scores) > 1 else 0,
                        "count": len(scores)
                    }
            
            return results
            
        except Exception as e:
            print(f"Error retrieving experiment results: {e}")
            raise
    
    def compare_experiments(self, experiment_names: List[str]) -> Dict[str, Any]:
        """
        Compare multiple experiments and generate comparison report
        """
        comparison = {
            "experiments": {},
            "metrics_comparison": {},
            "improvements": {},
            "regressions": {}
        }
        
        # Get results for each experiment
        for exp_name in experiment_names:
            try:
                results = self.get_experiment_results(exp_name)
                comparison["experiments"][exp_name] = results
            except Exception as e:
                print(f"Warning: Could not load experiment '{exp_name}': {e}")
                continue
        
        if len(comparison["experiments"]) < 2:
            print("Need at least 2 experiments for comparison")
            return comparison
        
        # Compare metrics across experiments
        for metric in self.metrics:
            metric_data = {}
            for exp_name, exp_data in comparison["experiments"].items():
                if metric in exp_data["metrics_summary"]:
                    metric_data[exp_name] = exp_data["metrics_summary"][metric]["mean"]
            
            if len(metric_data) >= 2:
                comparison["metrics_comparison"][metric] = metric_data
                
                # Find best and worst performing experiments for this metric
                best_exp = max(metric_data.items(), key=lambda x: x[1])
                worst_exp = min(metric_data.items(), key=lambda x: x[1])
                
                comparison["metrics_comparison"][metric + "_best"] = best_exp
                comparison["metrics_comparison"][metric + "_worst"] = worst_exp
        
        # Calculate improvements and regressions
        if len(experiment_names) >= 2:
            baseline = experiment_names[0]
            latest = experiment_names[-1]
            
            if baseline in comparison["experiments"] and latest in comparison["experiments"]:
                baseline_metrics = comparison["experiments"][baseline]["metrics_summary"]
                latest_metrics = comparison["experiments"][latest]["metrics_summary"]
                
                for metric in self.metrics:
                    if metric in baseline_metrics and metric in latest_metrics:
                        baseline_score = baseline_metrics[metric]["mean"]
                        latest_score = latest_metrics[metric]["mean"]
                        change = latest_score - baseline_score
                        change_pct = (change / baseline_score) * 100 if baseline_score > 0 else 0
                        
                        if change > 0.01:  # Significant improvement threshold
                            comparison["improvements"][metric] = {
                                "baseline": baseline_score,
                                "latest": latest_score,
                                "change": change,
                                "change_percent": change_pct
                            }
                        elif change < -0.01:  # Significant regression threshold
                            comparison["regressions"][metric] = {
                                "baseline": baseline_score,
                                "latest": latest_score,
                                "change": change,
                                "change_percent": change_pct
                            }
        
        return comparison
    
    def generate_trend_analysis(self, 
                              experiment_prefix: str = "shopping_agent_eval",
                              days_back: int = 30) -> Dict[str, Any]:
        """
        Generate trend analysis for experiments over time
        """
        # Get experiments from the last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        experiments = list(self.client.list_sessions(
            reference_example_type="dataset"
        ))
        
        # Filter experiments by prefix and date
        relevant_experiments = []
        for exp in experiments:
            if (exp.name and exp.name.startswith(experiment_prefix) and 
                exp.start_time and exp.start_time > cutoff_date):
                relevant_experiments.append(exp)
        
        # Sort by date
        relevant_experiments.sort(key=lambda x: x.start_time)
        
        trend_data = {
            "experiment_count": len(relevant_experiments),
            "date_range": {
                "start": relevant_experiments[0].start_time if relevant_experiments else None,
                "end": relevant_experiments[-1].start_time if relevant_experiments else None
            },
            "metrics_over_time": {metric: [] for metric in self.metrics},
            "trend_analysis": {}
        }
        
        # Collect metrics over time
        for exp in relevant_experiments:
            try:
                results = self.get_experiment_results(exp.name)
                for metric in self.metrics:
                    if metric in results["metrics_summary"]:
                        trend_data["metrics_over_time"][metric].append({
                            "date": exp.start_time,
                            "experiment": exp.name,
                            "score": results["metrics_summary"][metric]["mean"]
                        })
            except Exception as e:
                print(f"Warning: Could not analyze experiment '{exp.name}': {e}")
                continue
        
        # Calculate trends
        for metric, data_points in trend_data["metrics_over_time"].items():
            if len(data_points) >= 2:
                scores = [dp["score"] for dp in data_points]
                
                # Simple linear trend calculation
                n = len(scores)
                sum_x = sum(range(n))
                sum_y = sum(scores)
                sum_xy = sum(i * scores[i] for i in range(n))
                sum_x2 = sum(i * i for i in range(n))
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                trend_data["trend_analysis"][metric] = {
                    "slope": slope,
                    "direction": "improving" if slope > 0.001 else "declining" if slope < -0.001 else "stable",
                    "latest_score": scores[-1],
                    "best_score": max(scores),
                    "worst_score": min(scores),
                    "data_points": len(scores)
                }
        
        return trend_data
    
    def generate_detailed_report(self, 
                               experiment_name: str,
                               output_file: Optional[str] = None) -> str:
        """
        Generate a detailed evaluation report
        """
        try:
            results = self.get_experiment_results(experiment_name)
        except Exception as e:
            return f"Error generating report: {e}"
        
        report_lines = []
        report_lines.append(f"# Shopping Agent Evaluation Report")
        report_lines.append(f"")
        report_lines.append(f"**Experiment:** {experiment_name}")
        report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Total Runs:** {results['run_count']}")
        report_lines.append(f"")
        
        # Executive Summary
        report_lines.append(f"## Executive Summary")
        report_lines.append(f"")
        
        if results["metrics_summary"]:
            overall_scores = [data["mean"] for data in results["metrics_summary"].values()]
            overall_avg = statistics.mean(overall_scores)
            
            report_lines.append(f"- **Overall Performance:** {overall_avg:.3f}")
            report_lines.append(f"- **Best Metric:** {max(results['metrics_summary'].items(), key=lambda x: x[1]['mean'])[0]}")
            report_lines.append(f"- **Worst Metric:** {min(results['metrics_summary'].items(), key=lambda x: x[1]['mean'])[0]}")
            report_lines.append(f"")
        
        # Detailed Metrics
        report_lines.append(f"## Detailed Metrics")
        report_lines.append(f"")
        
        for metric, stats in results["metrics_summary"].items():
            report_lines.append(f"### {metric.replace('_', ' ').title()}")
            report_lines.append(f"")
            report_lines.append(f"- **Average Score:** {stats['mean']:.3f}")
            report_lines.append(f"- **Median Score:** {stats['median']:.3f}")
            report_lines.append(f"- **Range:** {stats['min']:.3f} - {stats['max']:.3f}")
            report_lines.append(f"- **Standard Deviation:** {stats['std']:.3f}")
            report_lines.append(f"- **Sample Size:** {stats['count']}")
            report_lines.append(f"")
        
        # Performance Issues
        report_lines.append(f"## Performance Issues")
        report_lines.append(f"")
        
        low_performing_runs = []
        error_runs = []
        
        for run in results["runs"]:
            if run["error"]:
                error_runs.append(run)
            elif run["feedback"]:
                avg_score = statistics.mean([fb["score"] for fb in run["feedback"].values() if fb["score"] is not None])
                if avg_score < 0.5:  # Threshold for low performance
                    low_performing_runs.append((run, avg_score))
        
        if error_runs:
            report_lines.append(f"### Errors ({len(error_runs)} runs)")
            for run in error_runs[:5]:  # Show first 5 errors
                report_lines.append(f"- Run {run['run_id'][:8]}: {run['error']}")
            if len(error_runs) > 5:
                report_lines.append(f"- ... and {len(error_runs) - 5} more errors")
            report_lines.append(f"")
        
        if low_performing_runs:
            report_lines.append(f"### Low Performing Runs ({len(low_performing_runs)} runs)")
            low_performing_runs.sort(key=lambda x: x[1])  # Sort by score
            for run, score in low_performing_runs[:5]:  # Show worst 5
                query = run["inputs"].get("query", "Unknown query")[:50]
                report_lines.append(f"- Score {score:.3f}: {query}...")
            report_lines.append(f"")
        
        # Recommendations
        report_lines.append(f"## Recommendations")
        report_lines.append(f"")
        
        if results["metrics_summary"]:
            # Find the metric with lowest performance
            worst_metric = min(results["metrics_summary"].items(), key=lambda x: x[1]["mean"])
            worst_name, worst_stats = worst_metric
            
            report_lines.append(f"### Priority Areas for Improvement")
            report_lines.append(f"")
            report_lines.append(f"1. **{worst_name.replace('_', ' ').title()}** (Score: {worst_stats['mean']:.3f})")
            
            # Provide specific recommendations based on the metric
            if worst_name == "workflow_execution":
                report_lines.append(f"   - Review query classification logic")
                report_lines.append(f"   - Optimize search query generation")
                report_lines.append(f"   - Improve error handling")
            elif worst_name == "search_accuracy":
                report_lines.append(f"   - Enhance search result filtering")
                report_lines.append(f"   - Improve product link detection")
                report_lines.append(f"   - Optimize Firecrawl integration")
            elif worst_name == "data_extraction":
                report_lines.append(f"   - Improve product information parsing")
                report_lines.append(f"   - Add more robust data validation")
                report_lines.append(f"   - Handle edge cases better")
            elif worst_name == "response_quality":
                report_lines.append(f"   - Enhance response generation prompts")
                report_lines.append(f"   - Improve product recommendation logic")
                report_lines.append(f"   - Add more contextual information")
            elif worst_name == "overall_performance":
                report_lines.append(f"   - Optimize workflow execution time")
                report_lines.append(f"   - Improve system reliability")
                report_lines.append(f"   - Enhance error recovery")
            
            report_lines.append(f"")
        
        # Generate the report
        report_content = "\n".join(report_lines)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"Report saved to: {output_file}")
            except Exception as e:
                print(f"Warning: Could not save report to file: {e}")
        
        return report_content
    
    def export_results_to_csv(self, 
                            experiment_name: str,
                            output_file: str) -> bool:
        """
        Export evaluation results to CSV for further analysis
        """
        try:
            results = self.get_experiment_results(experiment_name)
            
            # Prepare data for CSV
            rows = []
            for run in results["runs"]:
                row = {
                    "run_id": run["run_id"],
                    "query": run["inputs"].get("query", ""),
                    "execution_time": run["execution_time"],
                    "has_error": bool(run["error"]),
                    "error_message": run["error"] or ""
                }
                
                # Add metric scores
                for metric in self.metrics:
                    if metric in run["feedback"]:
                        row[f"{metric}_score"] = run["feedback"][metric]["score"]
                        row[f"{metric}_comment"] = run["feedback"][metric]["comment"]
                    else:
                        row[f"{metric}_score"] = None
                        row[f"{metric}_comment"] = ""
                
                rows.append(row)
            
            # Create DataFrame and save
            df = pd.DataFrame(rows)
            df.to_csv(output_file, index=False, encoding='utf-8')
            
            print(f"Results exported to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting results: {e}")
            return False


class PerformanceTracker:
    """
    Tracks agent performance over time and identifies trends
    """
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or Client()
        self.analyzer = EvaluationAnalyzer(client)
    
    def track_improvements(self, 
                         baseline_experiment: str,
                         current_experiment: str) -> Dict[str, Any]:
        """
        Track specific improvements between two experiments
        """
        comparison = self.analyzer.compare_experiments([baseline_experiment, current_experiment])
        
        tracking_result = {
            "baseline": baseline_experiment,
            "current": current_experiment,
            "overall_improvement": False,
            "improved_metrics": [],
            "regressed_metrics": [],
            "stable_metrics": [],
            "summary": {}
        }
        
        improved_count = len(comparison.get("improvements", {}))
        regressed_count = len(comparison.get("regressions", {}))
        
        tracking_result["overall_improvement"] = improved_count > regressed_count
        tracking_result["improved_metrics"] = list(comparison.get("improvements", {}).keys())
        tracking_result["regressed_metrics"] = list(comparison.get("regressions", {}).keys())
        
        # Calculate overall progress
        if comparison["experiments"]:
            baseline_scores = []
            current_scores = []
            
            baseline_data = comparison["experiments"].get(baseline_experiment, {})
            current_data = comparison["experiments"].get(current_experiment, {})
            
            for metric in self.analyzer.metrics:
                if (metric in baseline_data.get("metrics_summary", {}) and 
                    metric in current_data.get("metrics_summary", {})):
                    baseline_scores.append(baseline_data["metrics_summary"][metric]["mean"])
                    current_scores.append(current_data["metrics_summary"][metric]["mean"])
            
            if baseline_scores and current_scores:
                baseline_avg = statistics.mean(baseline_scores)
                current_avg = statistics.mean(current_scores)
                improvement_pct = ((current_avg - baseline_avg) / baseline_avg) * 100
                
                tracking_result["summary"] = {
                    "baseline_average": baseline_avg,
                    "current_average": current_avg,
                    "improvement_percent": improvement_pct,
                    "metrics_compared": len(baseline_scores)
                }
        
        return tracking_result


# Convenience functions
def analyze_experiment(experiment_name: str) -> Dict[str, Any]:
    """Convenience function to analyze a single experiment"""
    analyzer = EvaluationAnalyzer()
    return analyzer.get_experiment_results(experiment_name)


def compare_experiments(experiment_names: List[str]) -> Dict[str, Any]:
    """Convenience function to compare multiple experiments"""
    analyzer = EvaluationAnalyzer()
    return analyzer.compare_experiments(experiment_names)


def generate_report(experiment_name: str, output_file: Optional[str] = None) -> str:
    """Convenience function to generate a detailed report"""
    analyzer = EvaluationAnalyzer()
    return analyzer.generate_detailed_report(experiment_name, output_file)