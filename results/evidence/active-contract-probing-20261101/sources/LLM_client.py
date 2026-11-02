import json
import os
import requests

import openai


class LLMClient:
    """A client for interacting with large language models via API."""
    def __init__(self, model_name, api_key=None, api_base=None):
        """Initialize the LLM client with model name and API credentials."""
        self.model_name = model_name
        self.api_key = api_key if api_key else os.getenv("OPENAI_API_KEY")
        self.api_base = api_base if api_base else os.getenv("OPENAI_API_BASE")

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )

    def generate(self, user_prompt, system_prompt=None, response_format=None):
        """Generate text based on the provided prompt."""
        system_prompt = system_prompt if system_prompt else "You are a helpful assistant."

        # allow to retry at most three times
        for _ in range(3):
            if self.model_name.startswith("Qwen"):
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format=response_format if response_format else None,
                    extra_body={
                        "chat_template_kwargs": {"enable_thinking": False}  # default to True
                    },
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format=response_format if response_format else None
                )
            if response.choices:
                return response.choices[0].message.content
        return "Failed to generate response after 3 attempts."

    def exploration(self, tool_desc:str, explored_queries:str=None, suggestions_from_rewrite_agent:str=None)->tuple:
        """Generate exploration suggestions based on tool description and previous suggestions."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Query Proposal**.

## Goal
Generate natural, realistic user queries to explore the tool's functionality.  

## Instructions
1. Create a **realistic user query** that would require calling the tool **once**.  
2. Make the query **natural** — avoid exposing API names, parameter names, or technical jargon in the query.  
3. Provide **specific details** for all required parameters (e.g., instead of "address," say "123 Main Street, Manhattan, NY").  
4. Extract the parameters needed to call the tool in the exact format the tool expects.  
5. Avoid queries that are too similar to those already explored.  
6. Use the provided **exploration suggestions** to diversify coverage of the tool if provided.  

## Response Format
Return your response as a JSON object with exactly these fields:
- "User Query": A natural language query phrased as a user would ask
- "Parameters": The extracted parameters from the query, matching the tool's expected input format
"""
        user_prompt_data = {
            "Stage": "QueryProposal",
            "ToolDescription": tool_desc,
            "ExploredQueries": explored_queries if explored_queries else "[]",
            "Suggestions": suggestions_from_rewrite_agent if suggestions_from_rewrite_agent else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})
        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None, None
        
        return [response["User Query"]], [response["Parameters"]]

    def analysis(self, tool_desc:str, usage_examples:str, history:str=None)->str:
        """Analyze the tool's functionality based on exploration results."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Suggestion Generation**.

## Goal
Analyze the tool outputs and provide actionable suggestions to improve the tool's documentation.

## Instructions
1. Compare the given tool description with the outputs from explored queries.  
2. Check for:  
   - **Consistency**: Does the description match the tool's actual behavior?  
   - **Completeness**: Are important details missing?  
   - **Accuracy**: Is anything misleading or incorrect?  
   - **Conciseness**: Is there redundant or irrelevant information?  
3. Provide **concrete, constructive suggestions** for modifying the documentation.  
4. Focus on making the documentation **accurate, comprehensive, and concise**.
5. Return suggestions as a single coherent text string, not as a list or array.

## Response Format
Return your response as a JSON object with exactly this field:
- "Suggestions for tool description": A single text string containing all detailed, constructive modification suggestions for improving the tool documentation
"""

        user_prompt_data = {
            "Stage": "SuggestionGeneration",
            "ToolDescription": tool_desc,
            "UsageExamples": usage_examples if usage_examples else "[]",
            "History": history if history else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None
        return response["Suggestions for tool description"]

    def rewrite(self, tool_desc:str, usage_examples:str, suggestions:str, history:str=None)->tuple:
        """Rewrite the tool description based on provided suggestions."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Rewriting**.

## Goal
Refine the tool documentation so it is accurate, comprehensive, and concise, and propose the next exploration direction.

## Instructions
1. Rewrite the tool description so that it is:
   - **Accurate**: Reflects the tool's actual behavior.
   - **Comprehensive**: Covers all observed functionalities from explored queries.
   - **Concise**: Free of redundant or irrelevant details.
2. Propose a **direction for next exploration**:
   - Focus on aspects of the tool not yet explored.
   - Only give high-level directions, not a full query.

## Response Format
Return your response as a JSON object with exactly these fields:
- "Rewritten description": The improved tool description that is accurate, comprehensive, and concise
- "Suggestions for exploring": High-level directions for the next queries to further explore the tool
"""
        user_prompt_data = {
            "Stage": "Rewriting",
            "ToolDescription": tool_desc,
            "UsageExamples": usage_examples if usage_examples else "[]",
            "Suggestions": suggestions if suggestions else "[]",
            "History": history if history else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None, None
        return response["Rewritten description"], response["Suggestions for exploring"]
