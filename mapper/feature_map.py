import re
import json
import os
import glob

def parse_feature_file_with_outline(filepath):
    scenarios = []
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    scenario = None
    examples = []
    in_examples = False
    example_headers = []
    for line in lines:
        line = line.strip()
        if line.startswith("Scenario Outline:"):
            if scenario:
                if scenario.get("examples"):
                    scenarios.extend(expand_scenario_outline(scenario))
                else:
                    scenarios.append(scenario)
            scenario = {
                "name": line.split(":", 1)[1].strip(),
                "steps": [],
                "examples": []
            }
            examples = []
            in_examples = False
            example_headers = []
        elif line.startswith("Scenario:"):
            if scenario:
                if scenario.get("examples"):
                    scenarios.extend(expand_scenario_outline(scenario))
                else:
                    scenarios.append(scenario)
            scenario = {
                "name": line.split(":", 1)[1].strip(),
                "steps": [],
                "examples": []
            }
            in_examples = False
            example_headers = []
        elif line.startswith(("Given", "When", "Then", "And", "But")):
            if scenario:
                scenario["steps"].append(line)
        elif line.startswith("Examples:"):
            in_examples = True
            example_headers = []
        elif in_examples and "|" in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not example_headers:
                example_headers = cells
            else:
                example = dict(zip(example_headers, cells))
                examples.append(example)
        elif not line:
            in_examples = False
    if scenario:
        if scenario.get("examples"):
            scenarios.extend(expand_scenario_outline(scenario))
        else:
            scenarios.append(scenario)
    return scenarios

def expand_scenario_outline(scenario_outline):
    expanded = []
    for example in scenario_outline["examples"]:
        # Replace all <placeholder> in scenario name and steps
        name = scenario_outline["name"]
        for key, value in example.items():
            name = name.replace(f"<{key}>", value)
        steps = []
        for step in scenario_outline["steps"]:
            step_expanded = step
            for key, value in example.items():
                step_expanded = step_expanded.replace(f"<{key}>", value)
            steps.append(step_expanded)
        expanded.append({
            "name": name,
            "steps": steps,
            "example": example
        })
    return expanded

def step_expr_to_regex(expr):
    # Convert Cucumber expressions to regex (very basic)
    expr = re.sub(r"\{string\}", r'"[^"]*"', expr)
    expr = re.sub(r"\{int\}", r"\\d+", expr)
    expr = re.sub(r"\{[^\}]+\}", r".*", expr)
    return "^" + expr + "$"

def map_steps_to_defs(scenarios, step_defs):
    mapped = {}
    for scenario in scenarios:
        scenario_key = scenario["name"]
        mapped_steps = []
        for step in scenario["steps"]:
            # Remove Given/When/Then/And/But for matching
            step_text = re.sub(r"^(Given|When|Then|And|But)\s+", "", step)
            matched_def = None
            matched_calls = []
            for step_def in step_defs:
                if "expression" not in step_def:
                    continue
                pattern = step_expr_to_regex(step_def["expression"])
                if re.match(pattern, step_text):
                    matched_def = step_def["expression"]
                    matched_calls = step_def.get("calls", [])
                    break
            mapped_steps.append({
                "step_line": step,
                "matched_expression": matched_def,
                "calls": matched_calls
            })
        mapped[scenario_key] = {
            "example": scenario.get("example", {}),
            "steps": mapped_steps
        }
    return mapped

if __name__ == "__main__":
    features_dir = "src/features"
    step_defs_path = "scanner/scan_split/all_step_definitions.json"
    with open(step_defs_path) as f:
        step_defs = json.load(f)
    all_scenarios = []
    for feature_file in glob.glob(os.path.join(features_dir, "*.feature")):
        outlines = parse_feature_file_with_outline(feature_file)
        all_scenarios.extend(outlines)
    mapping = map_steps_to_defs(all_scenarios, step_defs)
    with open("scenario_step_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print("Scenario to step mapping written to scenario_step_mapping.json")
