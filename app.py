import streamlit as st
import json
from datetime import datetime

from mapper.dom_parser import parse_dom
from mapper.har_parser import parse_har
from mapper.cdp_parser import parse_cdp_events
from mapper.mapping_utils import advanced_map_api_to_dom
from mapper.prompt_builder import build_mapping_prompt, build_testgen_prompt

st.set_page_config(page_title="Playwright Test Generator", layout="wide")
st.title("GenAI-powered Playwright Test Generator")

# --- Session State ---
for key in ["ui_data", "api_data", "cdp_data", "ui_api_mappings", "ui_api_mapping_json"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "mappings" in key else ""

# --- Step and Instructions ---
step_defs = st.text_area("Step Definitions", height=150)

cdp_json_text = st.text_area("Paste CDP Recording JSON (optional)", height=200)
if cdp_json_text:
    try:
        cdp_json = json.loads(cdp_json_text)
        st.session_state.cdp_data = cdp_json
    except Exception as e:
        st.error(f"Invalid JSON: {e}")

# --- CDP Summary ---
cdp_summary = ""
if st.session_state.get("cdp_data"):
    cdp_summary = parse_cdp_events(st.session_state["cdp_data"])
    st.text_area("CDP Session Actions (summary)", value=cdp_summary, height=200)


# --- Uploads ---
dom_files = st.file_uploader("Upload DOM Snapshots (HTML or JSON)", type=['html', 'json'], accept_multiple_files=True)
har_file = st.file_uploader("Upload HAR File", type=['har'])
# --- Parse files ---
if dom_files:
    dom_contents = [f.read().decode("utf-8") for f in dom_files]
    st.session_state.ui_data = parse_dom(dom_contents)
if har_file:
    har_raw = har_file.read().decode("utf-8")
    st.session_state.api_data = parse_har(har_raw)

# --- UI ↔ API Mapping ---
if st.button("Advanced Map API fields to DOM elements"):
    dom_summary = json.dumps(st.session_state.ui_data, indent=2)
    har_summary = json.dumps(st.session_state.api_data, indent=2)
    cdp_summary = ""
    if st.session_state.get("cdp_data"):
        cdp_summary = parse_cdp_events(st.session_state["cdp_data"])
    mapping_prompt = build_mapping_prompt(
        dom_summary=dom_summary,
        har_summary=har_summary,
        cdp_summary=cdp_summary,
        extra_instructions=None  # or any mapping-specific instructions
    )
    st.text_area("Mapping Prompt sent to GenAI (for debugging)", value=mapping_prompt, height=300)
    # Call GenAI API to get mappings
    mappings = advanced_map_api_to_dom(
        dom_data=st.session_state.ui_data,
        api_data=st.session_state.api_data,
        cdp_data=st.session_state.get("cdp_data", []),
        prompt=mapping_prompt
    )
    st.session_state.ui_api_mappings = mappings
    st.session_state.ui_api_mapping_json = json.dumps(mappings, indent=2)

# --- Display & Edit Mappings ---
if st.session_state.get("ui_api_mappings"):
    st.subheader("UI ↔ API Mappings (Editable)")
    updated_mappings = []
    for idx, mapping in enumerate(st.session_state.ui_api_mappings):
        api_field = st.text_input(f"API Field {idx+1}", value=mapping['api_field'], key=f"api_field_{idx}")
        dom_elements = st.text_area(
            f"Mapped DOM Elements {idx+1} (comma-separated)", 
            value=", ".join(mapping['dom_elements']), 
            key=f"dom_elements_{idx}"
        )
        updated_mappings.append({
            "api_field": api_field,
            "dom_elements": [e.strip() for e in dom_elements.split(",") if e.strip()]
        })
        st.write("---")
    if st.button("Update Mappings"):
        st.session_state.ui_api_mappings = updated_mappings
        st.session_state.ui_api_mapping_json = json.dumps(updated_mappings, indent=2)


custom_instructions = st.text_area("Custom Instructions (optional)", height=100)

# --- Prompt and GenAI ---
if st.button("Generate Playwright Test"):
    # Collect test case details as needed, or use placeholders
    test_case_name = "Sample Test Case"
    description = "Generated from UI/API mapping and user steps"
    framework = "Playwright + Cucumber"
    language = "TypeScript"
    steps = step_defs
    mapping_json = st.session_state.get("ui_api_mapping_json", "")
    cdp_context = cdp_summary
    instructions = custom_instructions

    prompt = build_testgen_prompt(
        test_case_name=test_case_name,
        description=description,
        framework=framework,
        language=language,
        steps=steps,
        mapping_json=mapping_json,
        cdp_context=cdp_context,
        instructions=instructions
    )
    st.text_area("Prompt sent to GenAI (for debugging)", value=prompt, height=300)
  