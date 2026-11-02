import re
import os
import json
import random
import time
import requests
import numpy as np
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

from pydantic import BaseModel
from typing import Union


# Data Models
class Info(BaseModel):
    """Data model for tool information."""
    category: str
    tool_name: str
    api_name: str
    tool_input: Union[str, dict]
    strip: str

def sanitize_name(name):
    """
    Sanitize names by handling reserved keywords.
    
    Args:
        name (str): Original name
        
    Returns:
        str: Sanitized name
    """
    reserved_words = ["from", "class", "return", "false", "true", "id", "and", "", "ID"]
    if name in reserved_words:
        name = "is_" + name.lower()
    return name


def standardize_string(string):
    """
    Standardize string by removing special characters and normalizing format.
    
    Args:
        string (str): Input string
        
    Returns:
        str: Standardized string
    """
    # Replace non-alphanumeric characters with underscores
    string = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9_]", "_", string)
    # Remove duplicate underscores
    string = re.sub(r"(_)+", "_", string).lower()
    
    # Remove leading and trailing underscores
    string = string.strip("_")
    
    # Add prefix if starts with digit
    if string and string[0].isdigit():
        string = "get_" + string
    
    return string

def prepare_tool_name_and_url(tools_root, info):
    """
    Prepare tool name and import URL based on tool information.
    
    Args:
        tools_root (str): Root path for tools
        info (Info): Tool information object
        
    Returns:
        tuple: (tool_name, standard_category, api_name, code_string)
    """
    category = info.category
    standard_category = category.replace(" ", "_").replace(",", "_").replace("/", "_")
    standard_category = re.sub(r"[_, ]+", "_", standard_category)
    
    tool_name = info.tool_name
    api_name = sanitize_name(standardize_string(info.api_name))
    
    if not tool_name.endswith(f"_for_{standard_category}"):
        tool_name = standardize_string(info.tool_name)
        code_string = f"from {tools_root}.{standard_category}.{tool_name}.api import {api_name}"
        tool_name += f"_for_{standard_category}"
    else:
        tmp_tool_name = standardize_string(tool_name.replace(f"_for_{standard_category}", ""))
        code_string = f"from {tools_root}.{standard_category}.{tmp_tool_name}.api import {api_name}"
    
    return tool_name, standard_category, api_name, code_string


def process_api_error(response):
    """
    Process API response to identify and categorize errors.
    
    Args:
        response: API response object
        
    Returns:
        tuple: (return_dict, save_cache_flag, switch_flag)
    """
    save_cache_flag = False
    switch_flag = False
    response_str = str(response)
    
    error_patterns = {
        "timeout": "The request to the API has timed out",
        "api_not_working": "Your Client (working) ---> Gateway (working) ---> API (not working)",
        "unauthorized": ["Unauthorized", "unauthorized"],
        "unsubscribed": "You are not subscribed to this API.",
        "rate_limit": ["Too many requests", "You have exceeded", "you are being rate limited"],
        "access_restricted": "Access restricted. Check credits balance or enter the correct API key.",
        "gateway_error": "Oops, an error in the gateway has occurred.",
        "blocked": "Blocked User. Please contact your API provider.",
        "general_error": "error"
    }
    
    if error_patterns["timeout"] in response_str:
        return_dict = {"error": "API temporarily not working error...", "response": response}
    elif error_patterns["api_not_working"] in response_str:
        return_dict = {"error": "API not working error...", "response": response}
    elif any(pattern in response_str for pattern in error_patterns["unauthorized"]):
        save_cache_flag = True
        return_dict = {"error": "Unauthorized error...", "response": response}
    elif error_patterns["unsubscribed"] in response_str:
        switch_flag = True
        return_dict = {"error": "Unsubscribed error...", "response": response}
    elif any(pattern in response_str for pattern in error_patterns["rate_limit"]):
        switch_flag = True
        return_dict = {"error": "Rate limit error...", "response": response}
    elif error_patterns["access_restricted"] in response_str:
        switch_flag = True
        return_dict = {"error": "Rate limit error...", "response": response}
    elif error_patterns["gateway_error"] in response_str:
        switch_flag = True
        return_dict = {"error": "Gateway error...", "response": response}
    elif error_patterns["blocked"] in response_str:
        switch_flag = True
        return_dict = {"error": "Blocked error...", "response": response}
    elif error_patterns["general_error"] in response_str:
        return_dict = {"error": "Message error...", "response": response}
    else:
        save_cache_flag = True
        return_dict = {"error": "", "response": response}
    
    return return_dict, save_cache_flag, switch_flag


def execute_tool_function(toolbench_code_string, toolbench_api_name, toolbench_input_params_str):
    """
    Execute the tool function with given parameters.
    
    Args:
        toolbench_code_string (str): Import code string
        toolbench_api_name (str): API function name
        toolbench_input_params_str (str): Input parameters string
        
    Returns:
        tuple: (success_flag, switch_flag, response, save_cache)
    """
    success_flag = False
    switch_flag = False
    save_cache = False
    
    print(toolbench_code_string)
    try:
        exec(toolbench_code_string)
        eval_func_str = f"{toolbench_api_name}({toolbench_input_params_str})"
        new_func = eval(eval_func_str)
        response, save_cache, switch_flag = process_api_error(new_func)
        success_flag = True
    except Exception as e:
        response = {"error": f"Function executing {toolbench_code_string} error...\n{e}", "response": ""}
        save_cache = False
    
    return success_flag, switch_flag, response, save_cache


def truncate_dict_by_schema(origin_dict, schema_dict):
    """
    Recursively truncate dictionary based on provided schema.
    
    Args:
        origin_dict (dict): Original dictionary to truncate
        schema_dict (dict): Schema to follow for truncation
        
    Returns:
        dict: Truncated dictionary
    """
    for key, value in list(origin_dict.items()):
        if key not in schema_dict:
            del origin_dict[key]
        else:
            if isinstance(value, dict):
                truncate_dict_by_schema(value, schema_dict[key])
            elif isinstance(value, list) and value:
                if isinstance(value[0], dict):
                    for item in value:
                        truncate_dict_by_schema(item, schema_dict[key][0])
    return origin_dict


def shorten_observation(schema_root, response_dict, category, tool_name, api_name, strip_method):
    """
    Shorten observation response based on schema and strip method.
    
    Args:
        schema_root (str): Path to schema root
        response_dict (dict): Response dictionary
        category (str): Tool category
        tool_name (str): Tool name
        api_name (str): API name
        strip_method (str): Method for stripping data
        
    Returns:
        str: Shortened observation string
    """
    if strip_method == "filter" or (strip_method == "random" and random.random() > 0.5):
        if isinstance(response_dict["response"], dict):
            schema_path = os.path.join(schema_root, category, tool_name + ".json")
            if os.path.exists(schema_path):
                schema_dicts = json.load(open(schema_path, "r"))
                api_list = schema_dicts["api_list"]
                schema = None
                
                for schema_dict in api_list:
                    schema_api_name = sanitize_name(standardize_string(schema_dict["name"]))
                    if schema_api_name == api_name and len(schema_dict["schema"]) > 0:
                        schema = schema_dict["schema"]
                        break
                
                if schema is not None:
                    response_dict["response"] = truncate_dict_by_schema(response_dict["response"], schema)
    
    return str(response_dict["response"])


def get_rapidapi_response(input_dict, api_customization=False, 
                         tools_root="data.toolenv.tools", 
                         schema_root="data/toolenv/response_examples"):
    """
    Get response from RapidAPI for given tool input.
    
    Args:
        input_dict (dict): Input parameters dictionary
        api_customization (bool): Whether to use API customization
        tools_root (str): Root path for tools
        schema_root (str): Root path for response schemas
        
    Returns:
        dict: API response with error and response fields
    """
    info = Info(**input_dict)
    rapidapi_key = input_dict['rapidapi_key']

    tool_name, standard_category, api_name, code_string = prepare_tool_name_and_url(tools_root, info)
    tool_input = info.tool_input
    strip_method = info.strip
    
    # Parse tool input
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input) if tool_input else {}
        except Exception:
            print(f"Can not parse tool input into json: {tool_input}")
            return {"error": "Tool input parse error...\n", "response": ""}
    
    # Prepare input parameters string
    input_params_str = ""
    if tool_input:
        for key, value in tool_input.items():
            if isinstance(value, str):
                input_params_str += f'{key}="{value}", '
            else:
                input_params_str += f'{key}={value}, '
    
    if not api_customization:
        input_params_str += f"toolbench_rapidapi_key='{rapidapi_key}'"
    
    # Execute the tool function
    success_flag, switch_flag, response_dict, save_cache = execute_tool_function(
        code_string, api_name, input_params_str
    )
    
    # Shorten observation based on schema
    observation = shorten_observation(
        schema_root, response_dict, standard_category, 
        tool_name.replace(f"_for_{standard_category}", ""), api_name, strip_method
    )
    
    result = str(observation)[:2048]
    return {"error": response_dict['error'], "response": result}



def make_api_request(args, cate, tool_name_processed, api_name_processed, parameters):
    """
    Make API request to either local or remote endpoint.
    
    Args:
        args: Command line arguments
        cate (str): Category
        tool_name_processed (str): Processed tool name
        api_name_processed (str): Processed API name
        parameters (dict): API parameters
        
    Returns:
        dict: API response
    """
    if args.rapidapi_url is None:
        payload = {
            "category": cate,
            "tool_name": tool_name_processed,
            "api_name": api_name_processed,
            "tool_input": parameters,
            "strip": "filter",
            "rapidapi_key": os.getenv("RAPIDAPI_KEY", "your_rapidapi_key_here"),
        }
        return get_rapidapi_response(payload)
    else:
        # Using the self-server
        time.sleep(2)  # Rate limit: 30 per minute
        payload = {
            "category": cate,
            "tool_name": tool_name_processed,
            "api_name": api_name_processed,
            "tool_input": parameters,
            "strip": "filter",
            "toolbench_key": os.getenv("RAPIDAPI_KEY", "your_rapidapi_key_here"),
        }
        headers = {"toolbench_key": os.getenv("RAPIDAPI_KEY", "your_rapidapi_key_here")}
        timeout = None if args.rapidapi_url.endswith("virtual") else 15
        
        try:
            response = requests.post(args.rapidapi_url, json=payload, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            return {"error": "Timeout error...", "response": ""}
        
        if response.status_code != 200:
            return {"error": f"request invalid, data error. status_code={response.status_code}", "response": ""}
        
        try:
            return response.json()
        except:
            return {"error": "request invalid, data error", "response": ""}
        

def query_from_docs(documents_df):
    
    query = (documents_df.get('category_name', '') or '') + ', ' + \
    (documents_df.get('tool_name', '') or '') + ', ' + \
    (documents_df.get('api_name', '') or '') + ', ' + \
    (documents_df.get('api_description', '') or '') + \
    ', required_params: ' + json.dumps(documents_df.get('required_parameters', '')) + \
    ', optional_params: ' + json.dumps(documents_df.get('optional_parameters', '')) + \
    ', return_schema: ' + json.dumps(documents_df.get('template_response', ''))

    return query





# check the embedding similarity
def get_embedding(text, embedding_model):
    """
    Get embedding for text using the specified embedding model.
    
    Args:
        text (str): Input text to embed
        embedding_model: The embedding model to use
        
    Returns:
        list or None: Embedding vector or None if failed
    """
    try:
        embeddings = embedding_model.embed(text)
        if isinstance(text, str):
            return embeddings[0]
        return embeddings
    except Exception as e:
        print(f"Embedding error: {type(e)} - {e}")
        return None


def cosine_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1, vec2: Input vectors
        
    Returns:
        float: Cosine similarity score
    """
    vec1 = np.array(vec1).flatten()
    vec2 = np.array(vec2).flatten()
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def compute_similarity_and_bleu(reference_sentence, candidate_sentence, embedding_model):
    """
    Compute similarity and BLEU score between two sentences.
    
    Args:
        reference_sentence (str): Reference sentence
        candidate_sentence (str): Candidate sentence
        embedding_model: Embedding model for similarity computation
        
    Returns:
        float: Combined similarity and BLEU score
    """
    try:
        assert isinstance(reference_sentence, str) and isinstance(candidate_sentence, str)
    except Exception as e:
        print(f"reference_sentence: {reference_sentence}, \n candidate_sentence: {candidate_sentence}")
        raise e
    reference_embedding = get_embedding(reference_sentence, embedding_model)
    candidate_embedding = get_embedding(candidate_sentence, embedding_model)
    similarity = cosine_similarity(reference_embedding, candidate_embedding)

    reference = [reference_sentence.lower().split()]
    candidate = candidate_sentence.lower().split()

    smoothie = SmoothingFunction().method4
    bleu_score = sentence_bleu(reference, candidate, smoothing_function=smoothie)
    delta = (bleu_score + similarity) / 2
    return delta

def check_query_similarity(user_query, explored_queries_embeddings, embedding_model, threshold):
    """
    Check if the generated query is too similar to previous ones.
    
    Args:
        user_query (str): Current user query
        explored_queries_embeddings (list): List of previous query embeddings
        embedding_model: Embedding model
        threshold (float): Similarity threshold
        
    Returns:
        bool: True if query is sufficiently different, False otherwise
    """
    if not explored_queries_embeddings:
        return True
        
    cur_embedding = get_embedding(user_query, embedding_model)
    similarities = [cosine_similarity(emb, cur_embedding) for emb in explored_queries_embeddings]
    return all(sim < threshold for sim in similarities)


def process_retrieval_document_for_evolution(documents_df):
    ir_corpus = {} # docid -> text
    corpus2tool = {} # text -> category_name + tool_name + api_name
    original_docs = {} # docid -> original json
    for row in documents_df.itertuples():
        try:
            doc = json.loads(row.document_content)
        except json.JSONDecodeError:
            print(f"Error decoding JSON for docid {row.docid}: {row.document_content}")
            raise json.JSONDecodeError(f"Invalid JSON format for docid {row.docid}")
        try:
            ir_corpus[row.docid] = (doc.get('category_name', '') or '') + ', ' + \
            (doc.get('tool_name', '') or '') + ', ' + \
            (doc.get('api_name', '') or '') + ', ' + \
            (doc.get('api_description', '') or '') + \
            ', required_params: ' + json.dumps(doc.get('required_parameters', '')) + \
            ', optional_params: ' + json.dumps(doc.get('optional_parameters', '')) + \
            ', return_schema: ' + json.dumps(doc.get('template_response', ''))

            corpus2tool[(doc.get('category_name', '') or '') + ', ' + \
            (doc.get('tool_name', '') or '') + ', ' + \
            (doc.get('api_name', '') or '') + ', ' + \
            (doc.get('api_description', '') or '') + \
            ', required_params: ' + json.dumps(doc.get('required_parameters', '')) + \
            ', optional_params: ' + json.dumps(doc.get('optional_parameters', '')) + \
            ', return_schema: ' + json.dumps(doc.get('template_response', ''))] = doc['category_name'] + '[SEP]' + doc['tool_name'] + '[SEP]' + doc['api_name']

            original_docs[row.docid] = doc
        except Exception as e:
            print(doc)
            raise e
    return ir_corpus, corpus2tool, original_docs