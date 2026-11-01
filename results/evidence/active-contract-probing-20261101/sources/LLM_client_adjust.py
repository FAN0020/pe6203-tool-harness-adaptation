import json
import os
import requests

import openai

class LLMClientAdjust:
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

    def adjustment(self, tool_names: list[str], tool_desc:dict)->dict:
        """Generate adjusted tool description based on current description and exploration results."""
        
#         sys_prompt = """You are tasked with refining documentation for a set of tools that belong to the same cluster (i.e., they are similar in purpose or functionality). 
# The refined documents must make the fine-grained differences clear so that a language model can reliably select the correct tool.

# Steps:
# 1. Identify shared functionality:
#    - Summarize what all tools in this cluster have in common.
# 2. Identify fine-grained differences:
#    - For each tool, highlight distinctions in:
#      * Input/output format
#      * Constraints or limitations
#      * Domain-specific applicability
#      * Edge cases where one tool succeeds and another fails
#      * Unique example queries from the explored examples
# 3. Rewrite the tool documents:
#    - Emphasize each tool’s unique traits and specializations
#    - Minimize redundant wording across tools
#    - Add disambiguation cues, e.g., “Use this tool instead of X when …”
#    - Include example queries/responses that clarify correct usage
# 4. Output:
#    - For each tool, return the refined documentation
#    - Use structured formatting (sections, bullet points, comparisons)
#    - Ensure tools are clearly distinguishable and disambiguation-friendly

# Response format:
# - Return only valid JSON.
# - The JSON object must map each tool name (string) to its refined tool description (string).
# - Example:
# {
#   "tool_a": "Refined description for tool A...",
#   "tool_b": "Refined description for tool B..."
# }

# Style guidelines:
# - Be concise but precise
# - Explicitly contrast tools when necessary
# - Maintain a professional documentation style
# """
        sys_prompt = """You are refining documentation for a set of tools that belong to the same functional cluster.
Your goal is to slightly improve clarity and append a concise relational supplement to each tool’s existing description.
Do not rewrite or restyle the main content — keep it almost exactly as given.

===========================
INSTRUCTIONS
===========================

### STEP 1. Understand the Cluster
Briefly identify what these tools share in purpose or functionality.
(This is for your own reasoning; do not include this summary in the output.)

### STEP 2. Interpret Exploration Results
When analyzing example responses:
- `"LLM simulator is not available"` with an empty response means the tool is **broken for that input**,  
  but it may still work for **other inputs** via cached responses.
- Otherwise, treat the tool as functional.

### STEP 3. Prepare Core Content
Keep the original text of each tool’s documentation with only **minor edits** if needed for clarity or consistency.
Do **not** change tone, formatting, or structure.

### STEP 4. Append a Relational Supplement
After the original (slightly refined) content for each tool, **append** a short section labeled  
`### Relational Notes` (or similar) that summarizes:

- **Status:** Functional / Broken for some inputs (cache usable)  
- **Fallback Tools:** When and why to use other tools instead (e.g., “Use X when this tool fails or has no cached result.”)  
- **Overlap/Complementarity:** Any differences or preferences between tools in the cluster.  

Keep this supplement short (3–6 bullet points or 2–3 sentences total).

### STEP 5. Output Format
Return only valid JSON:
{
  "tool_a": "Original (lightly edited) description for tool A\n\n### Relational Notes\n- ...",
  "tool_b": "Original (lightly edited) description for tool B\n\n### Relational Notes\n- ..."
}

===========================
STYLE GUIDELINES
===========================
- Preserve the main content almost verbatim.
- Append relational notes instead of integrating them into the core text.
- Be concise, factual, and consistent.
- Mention other tools only where it improves disambiguation or fallback choice.
- Output nothing except the JSON object.
"""

        # separate the tool descriptions and the explored examples
        tool_descriptions = {key: tool['description'] for key, tool in tool_desc.items()}
        explored_examples = {key: tool['explored_examples'] for key, tool in tool_desc.items()}

        user_prompt_data = {
            "tool_descriptions": tool_descriptions,
            "explored_examples": explored_examples
        }
        user_prompt = json.dumps(user_prompt_data)
        response = self.generate(user_prompt, sys_prompt, response_format={"type": "json_object"})

        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None, None
                
        # check if all the keys in the generated response match the tool names
        #? This error handling code is not necessary, since the outside function can handle missing tool issue.
        # for name in tool_names:
        #     if name not in response:
        #         raise ValueError(f"Refinement document for tool '{name}' is missing.")

        return response