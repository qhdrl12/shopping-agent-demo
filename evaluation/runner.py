"""
Shopping Agent Evaluation Runner

Orchestrates the evaluation process:
1. Loads datasets from LangSmith
2. Runs agent inference on each example
3. Applies evaluation metrics
4. Stores results in LangSmith Experiments
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from langchain_core.messages import HumanMessage
from langsmith import Client
from langsmith.evaluation import aevaluate

from backend.workflow.unified_workflow import unified_workflow
from evaluation.evaluators import get_evaluators, get_parallel_evaluators


class ShoppingAgentRunner:
    """
    Main runner class for evaluating the shopping agent
    """
    
    def __init__(self, langsmith_client: Optional[Client] = None):
        self.client = langsmith_client or Client()
        self.workflow = unified_workflow.workflow
        self.evaluators = get_evaluators()  # LangSmith 호환을 위해 개별 평가자 사용
        self.parallel_manager = get_parallel_evaluators()  # 단일 쿼리 평가용 병렬 매니저
    
    async def run_agent(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the shopping agent on a single query and return structured results with detailed tracking
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Prepare initial state
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "query_type": "",
                "search_query": "",
                "search_parameters": "",
                "search_results": [],
                "search_metadata": {},
                "filtered_product_links": [],
                "product_data": [],
                "final_response": "",
                "suggested_questions": [],
                "current_step": ""
            }
            
            # Run the workflow with detailed tracking
            config = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 30
            }
            
            # Track execution details
            execution_trace = {
                "nodes_executed": [],
                "tool_calls": [],
                "all_messages": [],
                "state_transitions": [],
                "errors": []
            }
            
            final_state = None
            step_count = 0
            # Accumulate state data across all nodes
            accumulated_state = initial_state.copy()
            
            async for chunk in self.workflow.astream(initial_state, config):
                step_count += 1
                final_state = chunk
                
                # Track node execution and accumulate state
                for node_name, node_state in chunk.items():
                    # Manually accumulate important fields
                    key_fields = [
                        "query_type", "search_query", "search_parameters", 
                        "search_results", "search_metadata", "filtered_product_links",
                        "product_data", "extracted_products_count", "final_response", 
                        "suggested_questions", "current_step"
                    ]
                    
                    for field in key_fields:
                        if field in node_state and node_state[field] is not None:
                            # Special handling for lists and dicts to avoid overwriting with empty values
                            if isinstance(node_state[field], (list, dict)):
                                if node_state[field]:  # Only update if not empty
                                    accumulated_state[field] = node_state[field]
                            else:
                                accumulated_state[field] = node_state[field]
                    execution_trace["nodes_executed"].append({
                        "step": step_count,
                        "node": node_name,
                        "timestamp": time.time() - start_time,
                        "current_step": node_state.get("current_step", "")
                    })
                    
                    # Extract and track messages if they exist
                    if "messages" in node_state and node_state["messages"]:
                        for msg in node_state["messages"]:
                            if hasattr(msg, 'dict'):
                                msg_dict = msg.dict()
                            else:
                                msg_dict = {
                                    "content": getattr(msg, 'content', str(msg)),
                                    "type": type(msg).__name__,
                                    "node": node_name,
                                    "step": step_count
                                }
                            execution_trace["all_messages"].append(msg_dict)
                    
                    # Track tool usage
                    if node_name in ["search_products", "extract_product_data"]:
                        tool_info = {
                            "node": node_name,
                            "step": step_count,
                            "timestamp": time.time() - start_time,
                            "search_query": node_state.get("search_query", ""),
                            "search_parameters": node_state.get("search_parameters", ""),
                            "results_count": len(node_state.get("search_results", [])),
                            "products_found": len(node_state.get("product_data", []))
                        }
                        execution_trace["tool_calls"].append(tool_info)
                    
                    # Track state transitions
                    execution_trace["state_transitions"].append({
                        "step": step_count,
                        "node": node_name,
                        "state_snapshot": {
                            "query_type": node_state.get("query_type", ""),
                            "search_query": node_state.get("search_query", ""),
                            "current_step": node_state.get("current_step", ""),
                            "message_count": len(node_state.get("messages", [])),
                            "product_count": len(node_state.get("product_data", []))
                        }
                    })
            
            execution_time = time.time() - start_time
            
            # Extract results from accumulated state
            if final_state:
                # Use accumulated state that contains data from all nodes
                state = accumulated_state
                
                # Debug: Print accumulated state data
                print(f"\n🔍 Accumulated state debug:")
                print(f"  search_results: {len(state.get('search_results', []))}")
                print(f"  filtered_product_links: {len(state.get('filtered_product_links', []))}")
                print(f"  product_data: {len(state.get('product_data', []))}")
                print(f"  extracted_products_count: {state.get('extracted_products_count', 'N/A')}")
                print(f"  search_metadata: {state.get('search_metadata', {})}")
                print(f"  final_response length: {len(state.get('final_response', ''))}")
                print(f"  All state keys: {list(state.keys())}")
                
                # Create final answer from the most recent message with content
                final_answer = state.get("final_response", "")
                if not final_answer and execution_trace["all_messages"]:
                    # Get the last message with content
                    for msg in reversed(execution_trace["all_messages"]):
                        if msg.get("content") and msg["content"].strip():
                            final_answer = msg["content"]
                            break
                
                return {
                    "query": query,
                    "query_type": state.get("query_type", ""),
                    "search_query": state.get("search_query", ""),
                    "search_parameters": state.get("search_parameters", ""),
                    "search_results": state.get("search_results", []),
                    "search_metadata": state.get("search_metadata", {}),
                    "filtered_product_links": state.get("filtered_product_links", []),
                    "product_data": state.get("product_data", []),
                    "final_response": final_answer,
                    "suggested_questions": state.get("suggested_questions", []),
                    "current_step": state.get("current_step", ""),
                    "execution_time": execution_time,
                    "success": True,
                    "error": None,
                    # Enhanced tracking data for evaluation
                    "final_answer": final_answer,  # LangSmith 호환성
                    "messages": execution_trace["all_messages"],  # 모든 메시지 기록
                    "execution_trace": execution_trace,  # 상세 실행 추적
                    "workflow_stats": {
                        "total_steps": step_count,
                        "nodes_executed": len(execution_trace["nodes_executed"]),
                        "tool_calls_made": len(execution_trace["tool_calls"]),
                        "messages_generated": len(execution_trace["all_messages"]),
                        "execution_path": [node["node"] for node in execution_trace["nodes_executed"]]
                    }
                }
            else:
                return {
                    "query": query,
                    "execution_time": execution_time,
                    "success": False,
                    "error": "No final state received from workflow"
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "query": query,
                "execution_time": execution_time,
                "success": False,
                "error": str(e)
            }
    
    def create_target_function(self) -> Callable:
        """
        Create a target function for LangSmith evaluation
        """
        async def target_function(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """
            Target function that runs the agent and returns outputs
            """
            # 다양한 입력 필드명 시도
            query = (inputs.get("query") or 
                    inputs.get("input") or 
                    inputs.get("question") or 
                    inputs.get("text") or
                    inputs.get("prompt") or
                    "")
            
            # 만약 딕셔너리에 값이 하나만 있다면 그것을 사용
            if not query and len(inputs) == 1:
                query = list(inputs.values())[0]
            
            if not query:
                # 디버그를 위해 입력 구조 출력
                print(f"🔍 Debug - Available input keys: {list(inputs.keys())}")
                print(f"🔍 Debug - Input values: {inputs}")
                raise ValueError(f"No query found in inputs. Available keys: {list(inputs.keys())}")
            
            # Run the agent
            result = await self.run_agent(query)
            
            # Return in the format expected by LangSmith
            return {
                "output": result.get("final_response", ""),
                **result  # Include all other fields for evaluators
            }
        
        return target_function
    
    async def run_evaluation(self, 
                           dataset_name: str,
                           experiment_name: Optional[str] = None,
                           max_concurrency: int = 1,
                           sample_size: Optional[int] = None) -> str:
        """
        Run evaluation on a LangSmith dataset
        
        Args:
            dataset_name: Name of the dataset in LangSmith
            experiment_name: Name for the experiment (auto-generated if None)
            max_concurrency: Maximum number of concurrent evaluations
            sample_size: Limit number of examples to evaluate (None for all)
            
        Returns:
            Experiment ID
        """
        
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"shopping_agent_eval_{timestamp}"
        
        print(f"🚀 Starting evaluation: {experiment_name}")
        print(f"📊 Dataset: {dataset_name}")
        print(f"⚡ Max concurrency: {max_concurrency}")
        if sample_size:
            print(f"🔢 Sample size: {sample_size}")
        
        # Get dataset info
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            print(f"✅ Dataset found: {dataset.name} ({dataset.example_count} examples)")
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            raise
        
        # Create target function
        target_function = self.create_target_function()
        
        # Run evaluation
        try:
            results = await aevaluate(
                target_function,
                data=dataset_name,
                evaluators=self.evaluators,
                experiment_prefix=experiment_name,
                max_concurrency=max_concurrency,
                num_repetitions=1,
                client=self.client
            )
            
            experiment_url = f"https://smith.langchain.com/"
            
            print(f"✅ Evaluation completed!")
            print(f"📈 Experiment: {results.experiment_name}")
            print(f"🔗 Results: {experiment_url}")
            
            # Print summary statistics
            if hasattr(results, 'results'):
                scores = {}
                for result in results.results:
                    for eval_result in result.evaluation_results:
                        metric = eval_result.key
                        score = eval_result.score
                        if metric not in scores:
                            scores[metric] = []
                        if score is not None:
                            scores[metric].append(score)
                
                print("\n📊 Average Scores:")
                for metric, score_list in scores.items():
                    if score_list:
                        avg_score = sum(score_list) / len(score_list)
                        print(f"  {metric}: {avg_score:.3f} ({len(score_list)} samples)")
            
            return results.experiment_name
            
        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            raise
    
    def run_single_evaluation(self, query: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Evaluate a single query for testing purposes
        
        Args:
            query: Query to evaluate
            verbose: Whether to print detailed results
            
        Returns:
            Evaluation results
        """
        
        print(f"🔍 Evaluating single query: '{query}'")
        
        # Run the agent
        result = asyncio.run(self.run_agent(query))
        
        if not result.get("success", False):
            print(f"❌ Agent execution failed: {result.get('error', 'Unknown error')}")
            return result
        
        print(f"✅ Agent completed in {result['execution_time']:.2f}s")
        
        if verbose:
            print(f"📝 Response: {result.get('final_response', 'No response')[:200]}...")
            print(f"🏷️  Query type: {result.get('query_type', 'Unknown')}")
            print(f"🔍 Search query: {result.get('search_query', 'None')}")
            print(f"🛍️  Products found: {len(result.get('product_data', []))}")
            print(f"🔗 Filtered links: {len(result.get('filtered_product_links', []))}")
            print(f"📊 Search results: {len(result.get('search_results', []))}")
            
            # Debug data for evaluation
            print(f"\n🔍 Debug - Data for evaluation:")
            print(f"  product_data count: {len(result.get('product_data', []))}")
            print(f"  filtered_product_links count: {len(result.get('filtered_product_links', []))}")
            if result.get('product_data'):
                print(f"  First product sample: {list(result['product_data'][0].keys()) if result['product_data'] else 'None'}")
        
        # Run parallel evaluation by default
        inputs = {"query": query}
        print(f"🚀 Running parallel evaluation...")
        
        try:
            eval_results_list = asyncio.run(self.parallel_manager.evaluate_parallel(inputs, result))
            evaluation_results = {}
            for eval_result in eval_results_list:
                evaluation_results[eval_result["key"]] = eval_result
        except Exception as e:
            print(f"❌ Parallel evaluation failed: {e}")
            evaluation_results = {}
        
        # Calculate overall score
        if evaluation_results:
            overall_score = sum(r["score"] for r in evaluation_results.values()) / len(evaluation_results)
            print(f"🎯 Overall Score: {overall_score:.3f}")
        
        return {
            "agent_result": result,
            "evaluation_results": evaluation_results,
            "overall_score": overall_score if evaluation_results else 0.0
        }


class DatasetManager:
    """
    Helper class for managing LangSmith datasets
    """
    
    def __init__(self, client: Optional[Client] = None):
        self.client = client or Client()
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets"""
        datasets = list(self.client.list_datasets())
        return [
            {
                "name": ds.name,
                "id": ds.id,
                "description": ds.description,
                "example_count": ds.example_count,
                "created_at": ds.created_at
            }
            for ds in datasets
        ]
    
    def get_dataset_examples(self, dataset_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get examples from a dataset"""
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            examples = list(self.client.list_examples(dataset_id=dataset.id, limit=limit))
            
            return [
                {
                    "id": ex.id,
                    "inputs": ex.inputs,
                    "outputs": ex.outputs,
                    "created_at": ex.created_at
                }
                for ex in examples
            ]
        except Exception as e:
            print(f"Error loading dataset examples: {e}")
            return []
    
    def create_sample_dataset(self, 
                            dataset_name: str,
                            examples: List[Dict[str, Any]],
                            description: str = "") -> str:
        """
        Create a sample dataset for testing
        
        Args:
            dataset_name: Name for the new dataset
            examples: List of examples with 'query' and optionally 'expected_output'
            description: Dataset description
            
        Returns:
            Dataset ID
        """
        
        try:
            # Convert examples to LangSmith format
            langsmith_examples = []
            for i, example in enumerate(examples):
                langsmith_examples.append({
                    "inputs": {"query": example["query"]},
                    "outputs": {"expected_output": example.get("expected_output", "")},
                    "metadata": {"index": i}
                })
            
            # Create dataset
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description=description or f"Sample dataset with {len(examples)} examples"
            )
            
            # Add examples
            self.client.create_examples(
                inputs=[ex["inputs"] for ex in langsmith_examples],
                outputs=[ex["outputs"] for ex in langsmith_examples],
                metadata=[ex.get("metadata", {}) for ex in langsmith_examples],
                dataset_id=dataset.id
            )
            
            print(f"✅ Created dataset '{dataset_name}' with {len(examples)} examples")
            return dataset.id
            
        except Exception as e:
            print(f"❌ Error creating dataset: {e}")
            raise


# Convenience functions
async def run_evaluation(dataset_name: str, 
                        experiment_name: Optional[str] = None,
                        max_concurrency: int = 1,
                        sample_size: Optional[int] = None) -> str:
    """
    Convenience function to run evaluation
    """
    runner = ShoppingAgentRunner()
    return await runner.run_evaluation(
        dataset_name=dataset_name,
        experiment_name=experiment_name,
        max_concurrency=max_concurrency,
        sample_size=sample_size
    )


def test_single_query(query: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to test a single query
    """
    runner = ShoppingAgentRunner()
    return runner.run_single_evaluation(query=query, verbose=verbose)


def list_datasets() -> List[Dict[str, Any]]:
    """
    Convenience function to list all datasets
    """
    manager = DatasetManager()
    return manager.list_datasets()