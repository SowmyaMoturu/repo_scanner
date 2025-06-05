import json

def build_pom_method_prompt(intent_json, retrieved_context=None, extra_context=None):
    user_story = intent_json.get("user_story", "")
    # Use testFlow as steps if steps is not present
    steps = intent_json.get("steps") or intent_json.get("testFlow", [])
    if isinstance(steps, list):
        steps = "\n".join(steps)
    return f"""
You are a Playwright automation expert.

Given the following user intent:

User Story:
{user_story}

Steps:
{steps}

DOM Elements of interest:
{json.dumps(intent_json.get("ui_elements", []), indent=2)}

API fields expected:
{json.dumps(intent_json.get("api_fields", []), indent=2)}

{f"Retrieved context:\n{retrieved_context}" if retrieved_context else ""}

Generate Playwright-based Page Object Model methods to perform these actions.

Method signatures should reflect what the user is doing (e.g., search case ID, validate case details).
Do not include test logic or assertions here — only reusable page methods.

Output must be valid TypeScript Playwright POM methods only.
    """.strip()