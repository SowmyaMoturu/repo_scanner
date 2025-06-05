def build_pom_class_prompt(class_name: str, generated_methods: str, retrieved_context: str = None) -> str:
    """
    Builds a prompt for GenAI to create or extend a POM class.

    Args:
        class_name: Name of the POM class (e.g., CaseDetailsPage).
        generated_methods: String of method definitions to include.
        retrieved_context: Optional example POM classes or patterns.

    Returns:
        A complete prompt to send to the GenAI model.
    """
    prompt = f"""You are an expert Playwright + TypeScript test automation engineer.

Your task is to generate or extend a Page Object Model (POM) class in TypeScript using Playwright.

## Class Name
`{class_name}`

## Methods to include
```ts
{generated_methods}
```
"""
    if retrieved_context:
        prompt += f"\n## Example Context\n{retrieved_context}\n"
    return prompt

