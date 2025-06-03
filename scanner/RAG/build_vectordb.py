import os
import json

SCAN_SPLIT = "scanner/scan_split"
OUTPUT = os.path.join(SCAN_SPLIT, "rag_chunks.jsonl")

def load_json(path):
    with open(path) as f:
        return json.load(f)

def pom_chunks():
    for fname in os.listdir(SCAN_SPLIT):
        if fname.endswith(".json") and fname not in (
            "all_step_definitions.json", "all_step_definitions_linked.json",
            "scenario_step_mapping.json", "method_file_index.json", "all_class_parents.json"
        ):
            data = load_json(os.path.join(SCAN_SPLIT, fname))
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

def api_chunks():
    # If you have APIService.json or similar, treat as POM for now
    return pom_chunks()

def stepdef_chunks():
    steps = load_json(os.path.join(SCAN_SPLIT, "all_step_definitions_linked.json"))
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

def customworld_chunks():
    data = load_json(os.path.join(SCAN_SPLIT, "CustomWorld.json"))
    for func in data.get("functions", []):
        yield {
            "type": "customworld_method",
            "class": func.get("class_name"),
            "method": func.get("method"),
            "params": func.get("params"),
            "filepath": func.get("filepath"),
            "line": func.get("line"),
            "code": func.get("code")
        }

def main():
    with open(OUTPUT, "w") as out:
        for chunk in pom_chunks():
            out.write(json.dumps(chunk) + "\n")
        for chunk in stepdef_chunks():
            out.write(json.dumps(chunk) + "\n")
        for chunk in customworld_chunks():
            out.write(json.dumps(chunk) + "\n")
    print(f"Wrote RAG chunks to {OUTPUT}")

if __name__ == "__main__":
    main()