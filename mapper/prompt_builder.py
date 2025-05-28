def build_mapping_prompt(dom_summary, har_summary, cdp_summary=None, extra_instructions=None):
    with open("mapper/ui_api_prompt.md", "r", encoding="utf-8") as f:
        mapping_template = f.read()
    cdp_section = f"\n- **CDP Session:**\n{cdp_summary}\n" if cdp_summary else ""
    instructions_section = f"\n{extra_instructions}\n" if extra_instructions else ""
    prompt = mapping_template.format(
        dom_summary=dom_summary,
        har_summary=har_summary
    ) + cdp_section + instructions_section
    return prompt

def build_testgen_prompt(
    test_case_name,
    description,
    framework,
    language,
    steps,
    mapping_json,
    cdp_context=None,
    instructions=None
):
    with open("mapper/static_prompt.md", "r", encoding="utf-8") as f:
        static_template = f.read()
    prompt = static_template.format(
        test_case_name=test_case_name,
        description=description,
        framework=framework,
        language=language,
        steps=steps,
        mapping_json=mapping_json,
        cdp_section=f"\n{cdp_context}\n" if cdp_context else ""
    )
    if instructions:
        prompt += f"\n\nInstructions:\n{instructions}"
    return prompt