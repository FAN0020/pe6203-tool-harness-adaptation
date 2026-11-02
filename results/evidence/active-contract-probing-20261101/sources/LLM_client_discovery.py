import json
import os
import requests

import openai


class LLMClientDiscovery:
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

    def exploration(self, tool_desc:str, explored_queries:str=None, suggestions_from_rewrite_agent:str=None, similar_tools_docs: str=None)->tuple:
        """Generate exploration suggestions based on tool description and previous suggestions."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Query Proposal (Iterative Mode)**.

## Goal
Generate natural, realistic user queries to explore the tool’s functionality.

## Instructions
1. Generate exactly one query for each of the three tracks:
   - **Known (Overlap):** validate functionality already described in the current doc or strongly aligned with peers.
   - **Unknown-from-Peers (Comparative Frontier):** probe functionality described in peers but not yet confirmed in this tool.
   - **Unknown-Novel (Emergent Frontier):** probe for functionality not suggested by either current docs or peers (entirely new possibilities).
2. Each query must require calling the tool **once**.  
3. Make queries **natural** — avoid exposing API names, parameter names, or technical jargon.  
4. Provide **specific values** for all required parameters (e.g., “123 Main Street, Manhattan, NY” instead of “address”).  
5. Extract the parameters in the exact format the tool expects.  
6. Avoid queries too similar to those already in **ExploredQueries**.  
7. Use **Suggestions** (if any) and **SimilarToolsDocs** to guide query choice.  
8. For each query, include a short **Rationale**.

## Response Format
Return a JSON object with exactly these fields:
- "Stage": must be "QueryProposal"
- "KnownQuery": object with "User Query", "Parameters", "Rationale"
- "UnknownFromPeersQuery": object with "User Query", "Parameters", "Rationale"
- "UnknownNovelQuery": object with "User Query", "Parameters", "Rationale"
"""
        user_prompt_data = {
            "Stage": "QueryProposal",
            "ToolDescription": tool_desc,
            "ExploredQueries": explored_queries if explored_queries else "[]",
            "Suggestions": suggestions_from_rewrite_agent if suggestions_from_rewrite_agent else "[]",
            "SimilarToolsDocs": similar_tools_docs if similar_tools_docs else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None, None
        
        try:
            query_list = []
            parameters_list = []
            for key in ["KnownQuery", "UnknownFromPeersQuery", "UnknownNovelQuery"]:
                query_list.append(response[key]["User Query"])
                parameters_list.append(response[key]["Parameters"])
        except KeyError:
            raise ValueError("Response JSON is missing expected fields.")
        
        return query_list, parameters_list

    def analysis(self, tool_desc:str, usage_examples:str, history:str=None, similar_tools_docs:str=None)->str:
        """Analyze the tool's functionality based on exploration results."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Suggestion Generation**.

## Goal
Analyze the tool outputs and provide actionable suggestions to improve the tool’s documentation.

## Instructions
1. Compare the given tool description with the outputs from explored queries.  
2. Use **SimilarToolsDocs** to strengthen the analysis:
   - Identify overlaps: features present in both current and peer docs.  
   - Identify gaps: features documented in peers but missing here.  
   - Highlight limitations: unsupported features users may expect from peers.  
   - Borrow clarity: adopt clearer examples or phrasing from peers if useful.  
3. Incorporate insights from **Unknown-Novel** probes:
   - Flag new or emergent capacities that neither peers nor docs covered.  
   - Suggest how to position them clearly in the docs if real.  
4. Check for:
   - **Consistency**: Does the description match the tool’s actual behavior?  
   - **Completeness**: Are important details missing compared to peers and novel findings?  
   - **Accuracy**: Is anything misleading or incorrect?  
   - **Conciseness**: Is there redundant or irrelevant information?  
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
            "History": history if history else "[]",
            "SimilarToolsDocs": similar_tools_docs if similar_tools_docs else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None
        return response["Suggestions for tool description"]

    def rewrite(self, tool_desc:str, usage_examples:str, suggestions:str, history:str=None, similar_tools_docs:str=None)->tuple:
        """Rewrite the tool description based on provided suggestions."""
        sys_prompt = """You are an assistant that helps optimize API/tool documentation.  
Your current role is **Rewriting**.

## Goal
Refine the tool documentation so it is accurate, comprehensive, and concise, and propose the next exploration direction.

## Instructions
1. Rewrite the tool description so that it is:
   - **Accurate**: Reflects actual behavior confirmed from queries.  
   - **Comprehensive**: Covers all observed functionalities, including overlaps with peers and novel discoveries.  
   - **Concise**: Free of redundant or irrelevant details.  
2. Incorporate **SimilarToolsDocs** by:
   - Highlighting features aligned with peers (validations).  
   - Explicitly noting unsupported peer features (set expectations).  
   - Borrowing clearer examples or explanations where useful.  
3. Incorporate **Unknown-Novel findings** by:
   - Documenting any emergent capacities uncovered.  
   - Clearly flagging them as unique or newly discovered.  
4. Propose a **direction for next exploration**:
   - Focus on comparative frontiers (peer features not yet confirmed) and emergent frontiers (new, still ambiguous behaviors).  
   - Give high-level directions only, not full queries.

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
            "History": history if history else "[]",
            "SimilarToolsDocs": similar_tools_docs if similar_tools_docs else "[]"
        }
        user_prompt = json.dumps(user_prompt_data)

        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        # post-process to ensure valid json
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None, None
        return response["Rewritten description"], response["Suggestions for exploring"]
