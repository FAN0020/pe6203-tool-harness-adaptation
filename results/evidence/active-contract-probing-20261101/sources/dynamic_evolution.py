"""
Dynamic Tool Evolution with LLM Client

This module implements a tool evolution system that uses LLM agents to explore,
analyze, and refine tool descriptions through iterative interaction.
"""

import argparse
import json
import os
import pdb
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

from evolution.model.embedding_model import BGEEmbedder, BGERetriever, BGECluster
from evolution.model.LLM_client import LLMClient
from evolution.model.LLM_client_discovery import LLMClientDiscovery
from evolution.model.LLM_client_adjust import LLMClientAdjust
from evolution.utils import (
    compute_similarity_and_bleu,
    check_query_similarity,
    query_from_docs,
    make_api_request,
    sanitize_name,
    standardize_string,
    get_embedding,
)
from toolbench.utils import standardize, standardize_category, change_name


# Configuration
DEFAULT_EPISODES = 5
CONVERGENCE_THRESHOLD = 0.75
SIMILARITY_THRESHOLD = 0.9
RETRY_ATTEMPTS = 3

RELATION_SPLITTER = "### Relational Notes"


class ToolEvolutionProcessor:
    """Handles the tool evolution process with better organization."""
    
    def __init__(self, args):
        self.args = args
        self.embedding_model = BGEEmbedder()
        self.llm_client = None
        self.retriever = None
        self._retriever_lock = threading.Lock()  # Lock for thread-safe retriever access
        self._embedding_lock = threading.Lock()  # Lock for thread-safe embedding access

    def load_existing_results(self, save_path):
        """Load existing results from save path if it exists."""
        if os.path.exists(save_path):
            with open(save_path, 'r', encoding='utf-8') as f:
                finished_tools = json.load(f)
            return finished_tools, [tool['doc_id'] for tool in finished_tools]
        return [], []

    def save_results(self, finished_tools, save_path):
        """Save results to the specified path."""
        if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(finished_tools, f, indent=4)

    def setup_retrieval_system(self, time_idx, last_time_tools):
        """Setup retrieval system for similarity search."""
        if self.args.model_name.startswith("Qwen"):
            safe_model_name = self.args.model_name.replace("/", "_")
            tsv_path = os.path.join(self.args.corpus_folder, "discovered", f"time_{time_idx}_{safe_model_name}_retrieval.tsv")
        else:
            tsv_path = os.path.join(self.args.corpus_folder, "discovered", f"time_{time_idx}_retrieval.tsv")
        
        # Prepare data for retrieval
        tool_data = []
        for tool in last_time_tools:
            doc_id = tool["doc_id"]
            clean_tool = {k: v for k, v in tool.items() if k != "doc_id" and k != "explored_examples"}
            tool_data.append([doc_id, json.dumps(clean_tool)])
        
        # Save as TSV and setup retriever
        pd.DataFrame(tool_data, columns=['docid', 'document_content']).to_csv(tsv_path, sep='\t', index=False)
        
        if self.retriever is None:
            self.retriever = BGERetriever(corpus_tsv_path=tsv_path)
        else:
            self.retriever._update_corpus(tsv_path)

    def get_llm_response(self, method, time_idx, retrieved_tool_docs=None, **kwargs):
        """Centralized method for LLM responses to reduce code duplication."""
        if time_idx == 0:
            return getattr(self.llm_client, method)(**kwargs)
        else:
            return getattr(self.llm_client, method)(similar_tools_docs=retrieved_tool_docs, **kwargs)

    def generate_unique_queries(self, tool_description, explored_queries_str, suggestion_from_rewrite_agent, 
                              time_idx, retrieved_tool_docs, explored_queries_embeddings):
        """Generate unique queries using the explorer agent."""
        diff_query_list, diff_parameters_list = [], []
        
        for attempt in range(RETRY_ATTEMPTS):
            user_query_list, parameters_list = self.get_llm_response(
                'exploration', time_idx, retrieved_tool_docs,
                tool_desc=tool_description,
                explored_queries=explored_queries_str,
                suggestions_from_rewrite_agent=suggestion_from_rewrite_agent
            )
            
            if user_query_list is None or parameters_list is None:
                print("Explorer agent response is None, retrying...")
                continue
            
            for user_query, parameters in zip(user_query_list, parameters_list):
                if not explored_queries_embeddings or not self.thread_safe_check_similarity(
                    user_query, explored_queries_embeddings, SIMILARITY_THRESHOLD
                ):
                    diff_query_list.append(user_query)
                    diff_parameters_list.append(parameters)
            
            if diff_query_list:
                break
                
        return diff_query_list, diff_parameters_list

    def process_tool_examples(self, diff_query_list, diff_parameters_list, explored_queries, 
                            explored_queries_embeddings, explored_examples, tool_category, 
                            tool_name, api_name):
        """Process tool examples by making API calls."""
        current_example_list = []
        tool_name_processed = sanitize_name(standardize_string(tool_name))
        api_name_processed = sanitize_name(standardize_string(api_name))
        
        for user_query, parameters in zip(diff_query_list, diff_parameters_list):
            response = make_api_request(self.args, tool_category, tool_name_processed, 
                                      api_name_processed, parameters)
            
            # if response is too long (more than nearly 2000 tokens), truncate it
            if response and len(json.dumps(response["response"])) > 2000:
                response['response'] = json.dumps(response['response'])[:2000] + "...[truncated]"
                print("Response too long, truncated.")
            if response and len(json.dumps((response["error"]))) > 2000:
                response['error'] = json.dumps(response['error'])[:2000] + "...[truncated]"
                print("Error message too long, truncated.")

            explored_queries.append(user_query)
            explored_queries_embeddings.append(self.thread_safe_get_embedding(user_query))
            
            example = {
                'User Query': user_query,
                'Parameters': parameters,
                'API_Response': response
            }
            current_example_list.append(example)
            explored_examples.append(example)
            
        return current_example_list

    def evolve_tool_description_discovery(self, api, time_idx, retrieved_tool_docs=None) -> tuple[str, list]:
        """Main tool evolution logic for a single tool."""
        # Initialize variables
        tool_name, api_name, tool_category = api['tool_name'], api['api_name'], api['category_name']
        last_tool_description = api['api_description']
        required_parameters, optional_parameters = api['required_parameters'], api['optional_parameters']
        
        # Tracking variables
        explored_queries, explored_queries_embeddings, explored_examples = [], [], []
        suggestions, rewrite_description_history = [], [last_tool_description]
        rewrite_agent_history, suggestion_from_rewrite_agent = [], None

        # Retrieve similar tools if needed
        if time_idx > 0:
            current_tool_docs = {k: v for k, v in api.items() if k != 'api_description'}
            current_tool_docs['api_description'] = rewrite_description_history[-1]
            query = query_from_docs(current_tool_docs)
            _, retrieved_tool_docs = self.retriever.retrieving_balanced(query, top_k=5, return_full_docs=True)

        # Evolution episodes
        for episode in range(DEFAULT_EPISODES):
            tool_info = {
                'category': tool_category, 'name': api_name,
                'description': rewrite_description_history[-1],
                'required_parameters': required_parameters,
                'optional_parameters': optional_parameters
            }
            tool_description = str(tool_info)

            if time_idx > 0:
                _, retrieved_tool_docs = self.retriever.retrieving_balanced(query, top_k=5, return_full_docs=True)

            # Generate unique queries
            diff_query_list, diff_parameters_list = self.generate_unique_queries(
                tool_description, str(explored_queries), suggestion_from_rewrite_agent,
                time_idx, retrieved_tool_docs, explored_queries_embeddings
            )
            
            if not diff_query_list:
                # print("No unique queries generated, skipping iteration.")
                continue

            # Process examples
            current_example_list = self.process_tool_examples(
                diff_query_list, diff_parameters_list, explored_queries,
                explored_queries_embeddings, explored_examples, tool_category,
                tool_name, api_name
            )

            # Analysis and rewriting
            usage_examples_str = json.dumps(current_example_list)
            history_str = str(rewrite_description_history) if len(rewrite_description_history) > 1 else None


            suggestion_ans = self.get_llm_response(
                'analysis', time_idx, retrieved_tool_docs,
                tool_desc=tool_description,
                usage_examples=usage_examples_str,
                history=history_str
            )

            suggestions.append(suggestion_ans)

            rewritten_description, suggestions_for_exploring = self.get_llm_response(
                'rewrite', time_idx, retrieved_tool_docs,
                tool_desc=tool_info["description"],
                usage_examples=usage_examples_str,
                suggestions=suggestion_ans or "No suggestions provided.",
                history=history_str
            )
            if rewritten_description is None or suggestions_for_exploring is None:
                print("Rewrite agent response is None, skipping iteration.")
                continue

            # Update tracking variables
            if not isinstance(rewritten_description, str):
                rewritten_description = json.dumps(rewritten_description)
            rewrite_description_history.append(rewritten_description)
            suggestion_from_rewrite_agent = suggestions_for_exploring
            rewrite_agent_history.append({
                'Rewritten description': rewritten_description,
                'Suggestions for exploring': suggestions_for_exploring
            })

            # Check convergence
            if len(rewrite_description_history) > 1:
                reference, candidate = rewrite_description_history[-2], rewrite_description_history[-1]
                delta = self.thread_safe_compute_similarity_bleu(reference, candidate)
                if delta > CONVERGENCE_THRESHOLD:
                    break
        
        return rewrite_description_history[-1], explored_examples

    def evolve_tool_description_adjust(self, tool_cluster) -> list:
        """Adjust tool descriptions within a cluster, and return updated descriptions."""
        tool_names = []
        tool_desc = {}
        for tool in tool_cluster:
            category = standardize_category(tool['category_name'])
            tool_name = standardize(tool['tool_name'])
            api_name = change_name(standardize(tool['api_name']))
            key = api_name + f"_for_{tool_name}"
            key = key[-64:]  # ensure the key length is within 64 characters
            # key = category + '__' + tool_name + '__' + api_name
            tool_names.append(key)
            explored_examples = tool.get('explored_examples', [])
            if isinstance(explored_examples, str):
                try:
                    explored_examples = json.loads(explored_examples)
                except:
                    explored_examples = []
            
            # compress the length of the explored examples if too long
            for example in explored_examples:
                if 'API_Response' in example and isinstance(example['API_Response'], dict):
                    response_str = json.dumps(example['API_Response'])
                    if len(response_str) > 2000:
                        example['API_Response'] = response_str[:2000] + "...[truncated]"
            
            tool_desc[key] = {
                "description": tool['api_description'].split(RELATION_SPLITTER)[0],
                "explored_examples": explored_examples
            }
        adjusted_descriptions = self.llm_client.adjustment(tool_names, tool_desc)

        if adjusted_descriptions is not None:
            updated_descriptions = []
            for tool in tool_cluster:
                category = standardize_category(tool['category_name'])
                tool_name = standardize(tool['tool_name'])
                api_name = change_name(standardize(tool['api_name']))
                # name = category + '__' + tool_name + '__' + api_name
                name = api_name + f"_for_{tool_name}"
                name = name[-64:]  # ensure the name length is within 64 characters
                update_tool_docs = {k: v for k, v in tool.items() if k != 'api_description'}
                if name in adjusted_descriptions.keys() and isinstance(adjusted_descriptions[name], str):
                    update_tool_docs['api_description'] = adjusted_descriptions[name]
                elif name in adjusted_descriptions.keys() and isinstance(adjusted_descriptions[name], dict) and 'description' in adjusted_descriptions[name]:
                    update_tool_docs['api_description'] = adjusted_descriptions[name]['description']
                else:
                    update_tool_docs['api_description'] = tool['api_description']
                    print("Warning: Adjusted description missing or invalid, using original.")
                updated_descriptions.append(update_tool_docs)
            return updated_descriptions
        else:
            print("Adjustment agent failed to produce valid output.")
            return tool_cluster

    def thread_safe_retrieve(self, query, top_k=5):
        """Thread-safe retrieval method to handle single BGERetriever constraint."""
        with self._retriever_lock:
            if self.retriever is None:
                return None
            _, retrieved_tool_docs = self.retriever.retrieving_balanced(query, top_k=top_k, return_full_docs=True)
            return retrieved_tool_docs

    def thread_safe_get_embedding(self, text):
        """Thread-safe embedding computation."""
        with self._embedding_lock:
            return get_embedding(text, self.embedding_model)

    def thread_safe_check_similarity(self, query, embeddings, threshold):
        """Thread-safe similarity check."""
        with self._embedding_lock:
            return check_query_similarity(query, embeddings, self.embedding_model, threshold)

    def thread_safe_compute_similarity_bleu(self, reference, candidate):
        """Thread-safe similarity and BLEU computation."""
        with self._embedding_lock:
            return compute_similarity_and_bleu(reference, candidate, self.embedding_model)

    def process_single_tool(self, api, time_idx, joint_doc_id, last_time_tools):
        """Process a single tool - designed for parallel execution."""
        try:
            # Skip if already exists in previous time
            if api['doc_id'] in joint_doc_id:
                for last_api in last_time_tools:
                    if last_api['doc_id'] == api['doc_id']:
                        api['api_description'] = last_api['api_description']
                        break
                return api, False  # False indicates no new processing needed
            
            # Create a separate LLM client for this thread to avoid conflicts
            if time_idx == 0:
                thread_llm_client = LLMClient(
                    model_name=self.args.model_name,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    api_base=os.getenv("OPENAI_API_BASE")
                )
            else:
                thread_llm_client = LLMClientDiscovery(
                    model_name=self.args.model_name,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    api_base=os.getenv("OPENAI_API_BASE")
                )
            
            # Create a copy of the processor for thread-local processing
            # We'll temporarily replace the LLM client
            original_client = self.llm_client
            self.llm_client = thread_llm_client
            
            try:
                new_description, explored_examples = self.evolve_tool_description_discovery(api, time_idx)
                api['api_description'] = new_description
                api['explored_examples'] = explored_examples
                return api, True  # True indicates new processing completed
            finally:
                # Restore original client (though this might not be necessary in parallel execution)
                self.llm_client = original_client
                
        except Exception as e:
            print(f"Error processing tool {api.get('doc_id', 'unknown')}: {str(e)}")
            import traceback
            traceback.print_exc()
            return api, "error_save_original"

    def process_tools_parallel_discovery(self, tools_to_process, time_idx, joint_doc_id, last_time_tools, 
                               finished_tools, save_path, max_workers=None):
        """Process tools in parallel while maintaining thread safety for the retriever."""
        if max_workers is None:
            max_workers = min(len(tools_to_process), os.cpu_count() or 1)
        
        processed_tools = []
        progress_bar = tqdm(total=len(tools_to_process), desc="Processing tools in parallel")
        save_lock = threading.Lock()  # Thread-safe saving

        def thread_safe_save():
            """Thread-safe saving with the complete finished_tools list."""
            with save_lock:
                self.save_results(finished_tools, save_path)
                print(f"Saved intermediate results with {len(finished_tools)} tools.")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_tool = {
                executor.submit(self.process_single_tool, api, time_idx, joint_doc_id, last_time_tools): api
                for api in tools_to_process
            }
            
            # Process completed tasks
            for future in as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    processed_tool, was_processed = future.result()
                    processed_tools.append((processed_tool, was_processed))

                    if was_processed == True or was_processed == "error_save_original":
                        finished_tools.append(processed_tool)
                        
                        # Save every 10 NEWLY processed tools (not total count)
                        if len(finished_tools) % 10 == 0:
                            thread_safe_save()
                        
                        if was_processed == "error_save_original":
                            print(f"Saved original tool due to processing error: {processed_tool.get('doc_id', 'unknown')}")
                    
                    progress_bar.update(1)
                except Exception as e:
                    print(f"Tool {tool.get('doc_id', 'unknown')} generated an exception: {e}")
                    processed_tools.append((tool, False))
                    progress_bar.update(1)
        
        progress_bar.close()
        return processed_tools

    def process_tools_parallel_adjust(self, clustered_tools, adjusted_finished_tools, save_path, max_workers=None):
        """Process tool adjustments in parallel."""
        if max_workers is None:
            max_workers = min(len(clustered_tools), os.cpu_count() or 1)

        progress_bar = tqdm(total=len(clustered_tools), desc="Adjusting tool clusters in parallel")
        save_lock = threading.Lock()  # Thread-safe saving

        def thread_safe_save():
            """Thread-safe saving with the complete finished_tools list."""
            with save_lock:
                self.save_results(adjusted_finished_tools, save_path)
                print(f"Saved intermediate results with {len(adjusted_finished_tools)} tools.")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.evolve_tool_description_adjust, tool_cluster): tool_cluster
                for _, tool_cluster in clustered_tools.items()
            }

            for future in as_completed(futures):
                tool_cluster = futures[future]
                try:
                    adjusted_tools = future.result()
                    adjusted_finished_tools.extend(adjusted_tools)

                    if len(adjusted_finished_tools) % 10 == 0:
                        thread_safe_save()
                    progress_bar.update(1)
                except Exception as e:
                    print(f"Error processing cluster {tool_cluster}: {e}")
                    adjusted_finished_tools.extend(tool_cluster)  # Save original tools on error
                    progress_bar.update(1)
        
        progress_bar.close()
        return adjusted_finished_tools

    def filter_tools_for_processing(self, tools, joint_doc_id, last_time_tools, finished_doc_id):
        """Filter tools to determine which ones need processing."""
        tools_to_process = []
        
        for api in tools:
            # Skip if already exists in previous time
            if api['doc_id'] in joint_doc_id:
                for last_api in last_time_tools:
                    if last_api['doc_id'] == api['doc_id']:
                        api['api_description'] = last_api['api_description']
                        break
                continue
            
            # Skip if already processed
            if api['doc_id'] in finished_doc_id:
                print(f"Tool {api['doc_id']} already processed, skipping...")
                continue
                
            tools_to_process.append(api)
        
        return tools_to_process


def main(args):
    """Main function to run the tool evolution process."""
    processor = ToolEvolutionProcessor(args)
    
    # Initialize LLM client
    processor.llm_client = LLMClient(
        model_name=args.model_name,
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE")
    )

    # Process each time step
    for time_idx in range(args.time_step):  # Assuming a maximum of 5 time steps
        print(f"=== Time {time_idx} ===")

        # Load tools data
        corpus_path = os.path.join(args.corpus_folder, "original", f"time_{time_idx}.json")
        with open(corpus_path, 'r') as file:
            tools = json.load(file)

        last_time_tools, joint_doc_id = [], []
        
        if time_idx > 0:
            # Load previous corpus
            if args.model_name.startswith("Qwen"):
                safe_model_name = args.model_name.replace("/", "_")
                last_time_corpus_path = os.path.join(args.corpus_folder, "adjusted", f"time_{time_idx-1}_{safe_model_name}.json")
            else:
                last_time_corpus_path = os.path.join(args.corpus_folder, "adjusted", f"time_{time_idx-1}.json")
            with open(last_time_corpus_path, 'r') as file:
                last_time_tools = json.load(file)

            # Find intersection of tool IDs
            last_time_doc_id = [tool['doc_id'] for tool in last_time_tools]
            current_time_doc_id = [tool['doc_id'] for tool in tools]
            joint_doc_id = list(set(last_time_doc_id) & set(current_time_doc_id))
            
            # Filter tools and setup retrieval
            last_time_tools = [tool for tool in last_time_tools if tool['doc_id'] in joint_doc_id]
            processor.setup_retrieval_system(time_idx, last_time_tools)
            
            # Switch to discovery client
            processor.llm_client = LLMClientDiscovery(
                model_name=args.model_name,
                api_key=os.getenv("OPENAI_API_KEY"),
                api_base=os.getenv("OPENAI_API_BASE")
            )

        # Setup save path and load existing results
        if args.model_name.startswith("Qwen"):
            safe_model_name = args.model_name.replace("/", "_")
            args.save_path = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}_{safe_model_name}.json")
        else:
            args.save_path = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}.json")
        finished_tools, finished_doc_id = processor.load_existing_results(args.save_path)
        print(f"Loaded {len(finished_tools)} finished tools from previous results.")
        
        # Add previous optimized tools
        if time_idx > 0:
            for tool in last_time_tools:
                if tool['doc_id'] in joint_doc_id and tool['doc_id'] not in finished_doc_id:
                    finished_tools.append(tool)
                    finished_doc_id.append(tool['doc_id'])
            processor.save_results(finished_tools, args.save_path)

        # Process each tool
        tools_to_process = processor.filter_tools_for_processing(
            tools, joint_doc_id, last_time_tools, finished_doc_id
        )
        print(f"{len(tools_to_process)} tools to process out of {len(tools)} total tools.")
        
        if not tools_to_process:
            print("No tools to process for this time step.")
        else:
            # Stage 1 (Discovery): Process tools in parallel or sequentially based on args
            if args.parallel and len(tools_to_process) > 1:
                print(f"Processing {len(tools_to_process)} tools in parallel with max_workers={args.max_workers}")
                processed_results = processor.process_tools_parallel_discovery(
                    tools_to_process, time_idx, joint_doc_id, last_time_tools, 
                    finished_tools, args.save_path, args.max_workers  # Pass finished_tools and save_path
                )
                
                # Handle results from parallel processing
                for processed_tool, was_processed in processed_results:
                    if was_processed == True or was_processed == "error_save_original":
                        finished_doc_id.append(processed_tool['doc_id'])
            else:
                print(f"Processing {len(tools_to_process)} tools sequentially")
                for idx, api in enumerate(tqdm(tools_to_process, desc="Processing tools")):
                    finished_doc_id.append(api['doc_id'])

                    # Evolve tool description
                    new_description, explored_examples = processor.evolve_tool_description_discovery(api, time_idx)
                    api['api_description'] = new_description
                    api['explored_examples'] = explored_examples
                    finished_tools.append(api)

                    # Save intermediate results
                    if len(finished_tools) % 10 == 0:
                        processor.save_results(finished_tools, args.save_path)
            
            # Save final results
            processor.save_results(finished_tools, args.save_path)


        # Stage 2 (Adjustment): First cluster tools and then adjust descriptions
        if args.model_name.startswith("Qwen"):
            safe_model_name = args.model_name.replace("/", "_")
            args.save_path = os.path.join(args.corpus_folder, "adjusted", f"time_{time_idx}_{safe_model_name}.json")
        else:
            args.save_path = os.path.join(args.corpus_folder, "adjusted", f"time_{time_idx}.json")
        # check if the folder path exists, if not, create it
        if not os.path.exists(os.path.dirname(args.save_path)):
            os.makedirs(os.path.dirname(args.save_path))
        adjusted_finished_tools, adjusted_finished_doc_id = processor.load_existing_results(args.save_path)
        print(f"Loaded {len(adjusted_finished_tools)} finished tools from previous adjustment results.")

        # set the client and cluster for clustering the tools
        processor.llm_client = LLMClientAdjust(
            model_name=args.model_name,
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("OPENAI_API_BASE")
        )

        # Generate TSV file for clustering from discovered tools
        if args.model_name.startswith("Qwen"):
            safe_model_name = args.model_name.replace("/", "_")
            discovery_json_file = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}_{safe_model_name}.json")
            discovery_tsv_file = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}_{safe_model_name}.tsv")
        else:
            discovery_json_file = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}.json")
            discovery_tsv_file = os.path.join(args.corpus_folder, "discovered", f"time_{time_idx}.tsv")
        
        # Load discovered tools and create TSV for clustering
        if os.path.exists(discovery_json_file):
            with open(discovery_json_file, 'r', encoding='utf-8') as f:
                discovered_tools = json.load(f)
            
            # Prepare data for clustering
            tool_data = []
            for tool in discovered_tools:
                doc_id = tool["doc_id"]
                clean_tool = {k: v for k, v in tool.items() if k != "doc_id" and k != "explored_examples"}
                tool_data.append([doc_id, json.dumps(clean_tool)])
            
            # Save as TSV for clustering
            pd.DataFrame(tool_data, columns=['docid', 'document_content']).to_csv(discovery_tsv_file, sep='\t', index=False)
        else:
            print(f"Warning: Discovery file {discovery_json_file} not found. Skipping adjustment stage.")
            continue
        
        # Cluster tools based on category_name
        bge_cluster = BGECluster(corpus_tsv_path=discovery_tsv_file)
        clustered_tools = bge_cluster.clustering()

        # filtering the unprocessed tools in each cluster
        for cluster_id, tool_cluster in clustered_tools.items():
            clustered_tools[cluster_id] = [tool for tool in tool_cluster if tool['doc_id'] not in adjusted_finished_doc_id]

        # Check if there are any clusters with tools to process
        total_tools_to_adjust = sum(len(cluster) for cluster in clustered_tools.values())
        if total_tools_to_adjust == 0:
            print("No tools need adjustment - all already processed.")
        else:
            print(f"Adjusting {total_tools_to_adjust} tools across {len(clustered_tools)} clusters.")

            if args.parallel and len(clustered_tools) > 1:
                print(f"Adjusting {len(clustered_tools)} tool clusters in parallel with max_workers={args.max_workers}")
                adjusted_finished_tools = processor.process_tools_parallel_adjust(
                    clustered_tools, adjusted_finished_tools, args.save_path, args.max_workers
                )
            else:
                for cluster_id, tool_cluster in tqdm(clustered_tools.items(), desc="Adjusting tool clusters"):
                    # Filter out already processed tools in this cluster
                    if not tool_cluster:
                        print(f"All tools in cluster {cluster_id} already processed, skipping...")
                        continue
                    
                    updated_descriptions = processor.evolve_tool_description_adjust(tool_cluster)
                    
                    for tool, updated_tool in zip(tool_cluster, updated_descriptions):
                        if isinstance(updated_tool, dict):
                            adjusted_finished_tools.append(updated_tool)
                        else:
                            tool['api_description'] = updated_tool
                            adjusted_finished_tools.append(tool)
                        adjusted_finished_doc_id.append(tool['doc_id'])

                        if len(adjusted_finished_tools) % 10 == 0:
                            processor.save_results(adjusted_finished_tools, args.save_path)        # Save intermediate results
        
        processor.save_results(adjusted_finished_tools, args.save_path)

        print(f"Time {time_idx} processing complete. Results saved to {args.save_path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool Exploration and Analysis using LLMClient")
    parser.add_argument('--model_name', type=str, required=True, help='Model name for API access')
    parser.add_argument('--rapidapi_url', type=str, help='RapidAPI URL for tool access')
    parser.add_argument('--env', type=str, default='only_expanded_tools_group', help='Environment for tool access')
    parser.add_argument('--corpus_folder', type=str, default=None,
                        help='Path to the StableToolBench corpus folder. Defaults to server/dynamic/corpus/<env>.')
    parser.add_argument('--time_step', type=int, default=5, help='Time step for evolution process')
    parser.add_argument('--parallel', action='store_true', help='Enable parallel processing of tools')
    parser.add_argument('--max_workers', type=int, default=None, 
                        help='Maximum number of parallel workers (default: number of CPU cores)')
    args = parser.parse_args()
    
    # Set default max_workers if not specified
    if args.max_workers is None:
        args.max_workers = min(8, os.cpu_count() or 1)  # Conservative default

    # Validate corpus folder
    if args.corpus_folder is None:
        args.corpus_folder = os.path.join("server/dynamic/corpus", args.env)
    if not os.path.exists(args.corpus_folder):
        raise ValueError(f"Corpus folder {args.corpus_folder} does not exist.")

    main(args)
