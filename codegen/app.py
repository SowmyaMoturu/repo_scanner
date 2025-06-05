import os
import streamlit as st
import json
import openai


from process_inputs.parsers.dom_parser import parse_dom
from process_inputs.parsers.har_parser import parse_har
from prompt_builder.user_intent_prompt import parse_user_intent
from prompt_builder.pom_method_prompt import build_pom_method_prompt
from prompt_builder.pom_class_prompt import build_pom_class_prompt
from prompt_builder.step_calss_prompt import build_stepdef_class_prompt
from rag.retrieve import retrieve_similar_chunks

st.set_page_config(page_title="Playwright Test Generator", layout="wide")
st.title("GenAI-powered Playwright Test Generator")

# --- Session State Initialization ---
for key in ["ui_data", "api_data", "parsed_intent", "existing_stepdefs", "retrieved_chunks", "llm_response"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "data" in key or "chunks" in key else ""

# --- User Inputs ---
user_story = st.text_area("User Story", height=100)
instructions = st.text_area("Custom Instructions (optional)", height=100)

# --- Upload DOM and HAR ---
dom_files = st.file_uploader("Upload DOM Snapshots (HTML or JSON)", type=['html', 'json'], accept_multiple_files=True)
har_file = st.file_uploader("Upload HAR File", type=['har'])

# --- Upload Optional Existing StepDefs ---
uploaded_stepdefs_file = st.file_uploader("Upload Existing StepDefs (optional)", type=["ts"])
if uploaded_stepdefs_file:
    st.session_state.existing_stepdefs = uploaded_stepdefs_file.read().decode("utf-8")

# --- Parse DOM & HAR ---
if dom_files:
    dom_contents = [f.read().decode("utf-8") for f in dom_files]
    st.session_state.ui_data = parse_dom(dom_contents)
    st.success(f"Parsed {len(st.session_state.ui_data)} DOM elements.")

if har_file:
    har_raw = har_file.read().decode("utf-8")
    st.session_state.api_data = parse_har(har_raw)
    st.success(f"Parsed {len(st.session_state.api_data)} XHR/fetch requests.")

# --- Main Flow ---
if st.button("Generate Test"):
    st.subheader("🧠 Step 1: Intent Parsing")

    if not user_story.strip():
        st.error("Please provide a user story.")
    else:
         

        # Step 1: Parse Intent
        intent = parse_user_intent(
            user_story=user_story,
            instructions=instructions,
            dom_snapshot=json.dumps(st.session_state.ui_data),
            har_metadata=json.dumps(st.session_state.api_data)
        )
        st.session_state.parsed_intent = intent
        st.json(intent)

        # Step 2: Retrieve Similar POM Methods/Classes from Vectorstore
        st.subheader("🔍 Step 2: Retrieve Similar POM Methods/Classes")
        retrieved_chunks = retrieve_similar_chunks(user_story, k=5)
        st.session_state.retrieved_chunks = retrieved_chunks
        for idx, chunk in enumerate(retrieved_chunks):
            st.markdown(f"**Chunk {idx+1}:**")
            st.code(chunk["content"])
            st.json(chunk["metadata"])

        # Step 3: Build Prompt to Generate POM Method(s)
        st.subheader("🧪 Step 3: POM Method Generation")
        method_prompt = build_pom_method_prompt(intent, retrieved_context=retrieved_chunks)
        st.text_area("POM Method Prompt", value=method_prompt, height=250)
        st.info("→ Sending above prompt to OpenAI...")

        # Step 4: Send Prompt to OpenAI and Show Response
        openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        llm_response = ""
        if openai.api_key:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert Playwright test code generator."},
                        {"role": "user", "content": method_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.2,
                )
                llm_response = response.choices[0].message.content
                st.session_state.llm_response = llm_response
                st.text_area("LLM Response (POM Method)", value=llm_response, height=300)
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
        else:
            st.warning("OpenAI API key not found. Set it in Streamlit secrets or as an environment variable.")

        # Step 5: POM Class Generation/Extension
        st.subheader("🏗️ Step 5: POM Class Generation/Extension")
        generated_pom_class_name = intent.get("pages", [{}])[0].get("name", "CaseDetailsPage")
        generated_methods_str = llm_response or "async searchByCaseId(caseId: string) { ... }"
        pom_class_prompt = build_pom_class_prompt(
            class_name=generated_pom_class_name,
            generated_methods=generated_methods_str,
            retrieved_context=retrieved_chunks
        )
        st.text_area("POM Class Prompt", value=pom_class_prompt, height=300)
        st.code(generated_methods_str, language="typescript")

        # Step 6: Step Definition Generation
        st.subheader("🧩 Step 6: Step Definition Class Generation/Extension")
        stepdef_prompt = build_stepdef_class_prompt(
            user_intent=intent,
            generated_methods=generated_methods_str,
            pom_class_name=generated_pom_class_name,
            existing_stepdefs_context=st.session_state.get("existing_stepdefs")
        )
        st.text_area("Step Definitions Prompt", value=stepdef_prompt, height=300)

        if st.button("Generate Step Definitions"):
            stepdef_output = "/* Replace with your LLM-generated StepDef code */"
            st.code(stepdef_output, language="typescript")

# --- Optional: Show Final Parsed Intent ---
if st.session_state.parsed_intent:
    with st.expander("🧠 Parsed Intent JSON"):
        st.json(st.session_state.parsed_intent)

# --- Flow Summary Diagram ---
st.markdown("""
---
### 🧭 **Flow Summary**
```mermaid
graph TD
    A[User Inputs: Story, DOM, HAR] --> B[Intent Parser]
    B --> C[Vector Retrieval (POM examples)]
    C --> D[POM Method Prompt]
    D --> E[POM Class Prompt]
    E --> F[StepDef Prompt]
            """)