import json
import re
import os

def categorize_step(expression):
    if re.search(r'\bnavigate|go to|visit\b', expression, re.I):
        return "navigation"
    if re.search(r'\bclick|press|tap\b', expression, re.I):
        return "click"
    if re.search(r'\benter|fill|type\b', expression, re.I):
        return "input"
    if re.search(r'\bvalidate|should|expect|assert\b', expression, re.I):
        return "validation"
    if re.search(r'\bintercept|api\b', expression, re.I):
        return "api_interception"
    if re.search(r'\bif\b|\bfor\b|\bswitch\b', expression, re.I):
        return "control_flow"
    if re.search(r'\bworld\b', expression, re.I):
        return "state_management"
    return "other"

def categorize_method_code(code):
    if re.search(r'\b(route|intercept|waitForResponse|waitForRequest)\b', code):
        return "api_interception"
    if re.search(r'\bif\b|\bfor\b|\bswitch\b', code):
        return "control_flow"
    if re.search(r'\bthis\.world\b|\bworld\b', code):
        return "state_management"
    if re.search(r'\bexpect\b|\bshould\b|assert', code):
        return "validation"
    return "other"

def extract_methods_from_ts_file(filepath):
    """Extracts all methods from a TypeScript class file and categorizes them."""
    methods = []
    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()
        class_matches = re.finditer(r'class\s+(\w+)[^{]*\{(.*?)\n\}', code, re.DOTALL)
        for class_match in class_matches:
            class_name = class_match.group(1)
            class_body = class_match.group(2)
            # Find all methods in the class
            method_matches = re.finditer(r'(\w+)\s*\((.*?)\)\s*\{(.*?)\n\}', class_body, re.DOTALL)
            for m in method_matches:
                method_name = m.group(1)
                params = m.group(2)
                body = m.group(3)
                snippet = f"{method_name}({params}) {{\n{body}\n}}"
                category = categorize_method_code(snippet)
                # Pattern tagging (example: waitForResponse -> api_intercept)
                pattern = None
                if "waitForResponse" in snippet:
                    pattern = "api_intercept"
                elif "getByTestId" in snippet:
                    pattern = "testdata_usage"
                elif "world" in snippet:
                    pattern = "state_mgmt"
                methods.append({
                    "class": class_name,
                    "method": method_name,
                    "file": filepath,
                    "category": category,
                    "pattern": pattern or category,
                    "snippet": snippet
                })
    except Exception as e:
        pass
    return methods

def extract_typescript_method(filepath, class_name, method_name):
    """Extracts the TypeScript code for a given method in a class from a file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()
        # Find the class
        class_pattern = re.compile(rf'class\s+{re.escape(class_name)}[^\{{]*\{{(.*?)\n\}}', re.DOTALL)
        class_match = class_pattern.search(code)
        if not class_match:
            return None
        class_body = class_match.group(1)
        # Find the method
        method_pattern = re.compile(rf'(\w+\s+)?{re.escape(method_name)}\s*\((.*?)\)\s*\{{(.*?)\n\}}', re.DOTALL)
        for m in method_pattern.finditer(class_body):
            return f"{method_name}({m.group(2)}) {{\n{m.group(3)}\n}}"
    except Exception as e:
        return None

def score_example(snippet):
    score = 0
    code = snippet.get("snippet", "")
    # Prefer async/await
    if "async " in code or "await " in code:
        score += 2
    # Prefer comments
    if "//" in code or "/**" in code:
        score += 1
    # Prefer getByTestId or best selectors
    if "getByTestId" in code:
        score += 2
    # Penalize TODOs or console.log
    if "TODO" in code or "console.log" in code:
        score -= 2
    # Prefer medium length (not too short/long)
    if 5 < len(code.splitlines()) < 40:
        score += 1
    return score

def select_best_examples(examples, top_n=2):
    # Prefer manually approved examples first
    approved = [ex for ex in examples if ex.get("approved") is True]
    # If manual_score is present, sort by it (descending)
    scored = sorted(
        [ex for ex in examples if ex not in approved],
        key=lambda ex: (ex.get("manual_score", 0), score_example(ex)),
        reverse=True
    )
    # Combine approved and top scored
    selected = approved[:top_n] + scored[:max(0, top_n - len(approved))]
    return selected

def extract_standalone_functions_from_ts_file(filepath):
    """Extracts all standalone (non-class) functions from a TypeScript file."""
    functions = []
    try:
        with open(filepath, encoding="utf-8") as f:
            code = f.read()
        # Match function declarations: function foo(...) { ... }
        func_pattern = re.compile(r'function\s+(\w+)\s*\((.*?)\)\s*\{([\s\S]*?)^\}', re.MULTILINE)
        for m in func_pattern.finditer(code):
            func_name = m.group(1)
            params = m.group(2)
            body = m.group(3)
            snippet = f"function {func_name}({params}) {{\n{body}\n}}"
            category = categorize_method_code(snippet)
            pattern = None
            if "waitForResponse" in snippet:
                pattern = "api_intercept"
            elif "getByTestId" in snippet:
                pattern = "testdata_usage"
            elif "world" in snippet:
                pattern = "state_mgmt"
            functions.append({
                "function": func_name,
                "file": filepath,
                "category": category,
                "pattern": pattern or category,
                "snippet": snippet
            })
        # Match arrow functions: const foo = (...) => { ... }
        arrow_pattern = re.compile(r'const\s+(\w+)\s*=\s*\((.*?)\)\s*=>\s*\{([\s\S]*?)^\}', re.MULTILINE)
        for m in arrow_pattern.finditer(code):
            func_name = m.group(1)
            params = m.group(2)
            body = m.group(3)
            snippet = f"const {func_name} = ({params}) => {{\n{body}\n}}"
            category = categorize_method_code(snippet)
            pattern = None
            if "waitForResponse" in snippet:
                pattern = "api_intercept"
            elif "getByTestId" in snippet:
                pattern = "testdata_usage"
            elif "world" in snippet:
                pattern = "state_mgmt"
            functions.append({
                "function": func_name,
                "file": filepath,
                "category": category,
                "pattern": pattern or category,
                "snippet": snippet
            })
    except Exception as e:
        pass
    return functions

def build_code_example_library_with_patterns(step_defs_path, page_object_dir, output_path):
    with open(step_defs_path) as f:
        step_defs = json.load(f)

    # Index TypeScript files by class name
    ts_files = {}
    for root, _, files in os.walk(page_object_dir):
        for file in files:
            if file.endswith(".ts"):
                filepath = os.path.join(root, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                # Find all classes in the file
                for match in re.finditer(r'class\s+(\w+)', content):
                    ts_files[match.group(1)] = filepath

    library = {}

    # Multi-file example grouping for patterns like api_intercept
    for step in step_defs:
        category = categorize_step(step["expression"])
        # Detect pattern for grouping (e.g., if any call uses waitForResponse)
        pattern = None
        code_snippets = []
        for call in step.get("calls", []):
            obj = call.get("object")
            method = call.get("method")
            if obj and method:
                class_name = obj.replace("pageObjects.", "") if obj.startswith("pageObjects") else obj
                ts_file = ts_files.get(class_name)
                if ts_file:
                    snippet = extract_typescript_method(ts_file, class_name, method)
                    if snippet:
                        code_snippets.append({
                            "class": class_name,
                            "method": method,
                            "file": ts_file,
                            "snippet": snippet
                        })
                        if "waitForResponse" in snippet:
                            pattern = "api_intercept"
                        elif "getByTestId" in snippet:
                            pattern = "testdata_usage"
                        elif "world" in snippet:
                            pattern = "state_mgmt"
        example = {
            "step": step["expression"],
            "calls": [f"{call['object']}.{call['method']}" for call in step.get("calls", []) if call.get("object") and call.get("method")],
            "snippets": code_snippets,
            "pattern": pattern or category
        }
        library.setdefault(example["pattern"], []).append(example)

    # Add all categorized methods and standalone functions from page objects
    for root, _, files in os.walk(page_object_dir):
        for file in files:
            if file.endswith(".ts"):
                filepath = os.path.join(root, file)
                methods = extract_methods_from_ts_file(filepath)
                for m in methods:
                    entry = {
                        "class": m["class"],
                        "method": m["method"],
                        "file": m["file"],
                        "snippet": m["snippet"],
                        "pattern": m["pattern"]
                    }
                    library.setdefault(entry["pattern"], []).append(entry)
                # Standalone functions
                functions = extract_standalone_functions_from_ts_file(filepath)
                for f in functions:
                    entry = {
                        "function": f["function"],
                        "file": f["file"],
                        "snippet": f["snippet"],
                        "pattern": f["pattern"]
                    }
                    library.setdefault(entry["pattern"], []).append(entry)

    # Only keep the best N examples per pattern
    for pattern, examples in library.items():
        library[pattern] = select_best_examples(examples, top_n=2)

    with open(output_path, "w") as f:
        json.dump(library, f, indent=2)
    print(f"Code example library (with patterns and multi-file grouping) written to {output_path}")

def assemble_prompt_from_library(library, required_patterns, extra_patterns=None, top_n=1):
    prompt_sections = []
    for pattern in required_patterns + (extra_patterns or []):
        examples = library.get(pattern, [])
        for ex in select_best_examples(examples, top_n=top_n):
            # If grouped snippets (multi-file example)
            if "snippets" in ex:
                for snippet in ex["snippets"]:
                    prompt_sections.append(
                        f"```typescript\n// file: {snippet.get('file')}\n{snippet.get('snippet')}\n```"
                    )
            # If single snippet
            elif "snippet" in ex:
                prompt_sections.append(
                    f"```typescript\n// file: {ex.get('file')}\n{ex.get('snippet')}\n```"
                )
    return "\n\n".join(prompt_sections)

# Usage:
# build_code_example_library_with_patterns(
#     "scanner/scan_split/all_step_definitions.json",
#     "src/pages",  # or your page object directory
#     "scanner/scan_split/code_example_library_with_patterns.json"
# )