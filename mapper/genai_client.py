import openai
import os

def call_genai_api(prompt, model="gpt-4", api_key=None):
    openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()