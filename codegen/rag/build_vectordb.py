import os
import json
from collections import defaultdict

OUTPUT_DIR = "codegen/output"
OUTPUT = os.path.join(OUTPUT_DIR, "RAG", "rag_chunks.jsonl")

def load_json(path):
    with open(path) as f:
        return json.load(f)

def pom_chunks():
    for fname in os.listdir(OUTPUT_DIR):
        if fname.endswith(".json") and fname not in (
            "all_step_definitions.json", "all_step_definitions_linked.json",
            "scenario_step_mapping.json", "method_index.json", "all_class_parents.json"
        ):
            data = load_json(os.path.join(OUTPUT_DIR, fname))
            for func in data.get("functions", []):
                yield {
                    "type": "pom_method",
                    "class": func.get("class_name"),
                    "method": func.get("method"),
                    "params": func.get("params"),
                    "filepath": func.get("filepath"),
                    "line": func.get("line"),
                    "code": func.get("code")
                }

def pom_class_chunks():
    # Group all methods by class
    class_map = defaultdict(list)
    file_map = {}
    for fname in os.listdir(OUTPUT_DIR):
        if fname.endswith(".json") and fname not in (
            "all_step_definitions.json", "all_step_definitions_linked.json",
            "scenario_step_mapping.json", "method_index.json", "all_class_parents.json"
        ):
            data = load_json(os.path.join(OUTPUT_DIR, fname))
            for func in data.get("functions", []):
                class_name = func.get("class_name")
                if class_name:
                    class_map[class_name].append(func)
                    if "filepath" in func:
                        file_map[class_name] = func["filepath"]
    for class_name, methods in class_map.items():
        class_code = "\n\n".join(m.get("code", "") for m in methods if m.get("code"))
        method_names = [m.get("method") for m in methods if m.get("method")]
        yield {
            "type": "pom_class",
            "class_name": class_name,
            "filepath": file_map.get(class_name),
            "method_names": method_names,
            "code": class_code
        }

def api_chunks():
    # If you have APIService.json or similar, treat as POM for now
    return pom_chunks()

def stepdef_chunks():
    steps = load_json(os.path.join(OUTPUT_DIR, "all_step_definitions_linked.json"))
    for step in steps:
        yield {
            "type": "step_definition",
            "step_keyword": step.get("step_keyword"),
            "expression": step.get("expression"),
            "location": step.get("location"),
            "params": step.get("params"),
            "calls": step.get("calls"),
            "code": step.get("code")
        }

def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True) 
    with open(OUTPUT, "w") as out:
        for chunk in pom_chunks():
            out.write(json.dumps(chunk) + "\n")
        for chunk in pom_class_chunks():
            out.write(json.dumps(chunk) + "\n")
        for chunk in stepdef_chunks():
            out.write(json.dumps(chunk) + "\n")
        # If you have customworld_chunks, add here
        # for chunk in customworld_chunks():
        #     out.write(json.dumps(chunk) + "\n")
    print(f"Wrote RAG chunks to {OUTPUT}")

if __name__ == "__main__":
    main()