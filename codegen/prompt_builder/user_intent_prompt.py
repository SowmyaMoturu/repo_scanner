import openai
import json
import os

openai.api_key = "your_openai_api_key"

def parse_user_intent(user_story: str, instructions: str = "", dom_snapshot: str = "", har_metadata: str = "") -> dict:
    prompt = f"""
You are an intelligent assistant that transforms user input into structured test automation metadata.
You will receive:
- A user story (natural language)
- Optional developer instructions
- Optional DOM snapshot (HTML or key tags)
- Optional HAR metadata (API calls observed)

---

### USER STORY:
{user_story}

### INSTRUCTIONS:
{instructions}

### DOM SNAPSHOT:
{dom_snapshot[:1000]}  <!-- Limit to avoid large payload -->

### HAR METADATA:
{har_metadata[:1500]}

---

### TASK:
Return a JSON object in the following format:
{{
  "pages": [
    {{
      "name": "<Name of Page Object Class>",
      "actions": [
        {{
          "name": "<MethodName>",
          "description": "<What it does>",
          "inputParams": ["<param1>", "<param2>"],
          "assertions": ["<optional expectations>"]
        }}
      ]
    }}
  ],
  "intercepts": [
    {{
      "api": "<API endpoint to intercept>",
      "validateAgainst": "<What to compare API response to>"
    }}
  ],
  "testFlow": [
    "<Step-by-step test flow extracted from the story>"
  ]
}}

Be as accurate and concise as possible. Do not hallucinate values. Use inferred context where necessary.

---

### JSON OUTPUT:
"""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "..."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.2,
    )
    result = response.choices[0].message.content
    
    try:
        parsed_output = json.loads(result)
    except json.JSONDecodeError:
        print("⚠️ Warning: LLM returned non-JSON content. Manual parsing needed.")
        parsed_output = {"error": "Invalid JSON from LLM", "raw_output": result}
    
    return parsed_output
