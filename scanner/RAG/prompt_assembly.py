def build_rag_prompt(user_story, dom_snapshot, har_data, retrieved_docs, always_include_patterns):
    context = "\n\n".join([doc.page_content for doc in always_include_patterns + retrieved_docs])
    prompt = f"""
You are a Playwright automation expert.
Given the following user story:
{user_story}

DOM snapshot:
{dom_snapshot}

HAR data:
{har_data}

Code context:
{context}

Generate Playwright code (POM, step-defs, etc.) for this user story, using the patterns and context above.
"""
    return prompt