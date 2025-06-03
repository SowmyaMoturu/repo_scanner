from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from scanner.RAG.build_vectordb import load_code_chunks  # Your function to load all code chunks

def build_vectorstore(chunks, persist_directory="vectorstore"):
    embedding = OpenAIEmbeddings()  # Or your custom embedding
    vectorstore = Chroma.from_documents(
        chunks,
        embedding,
        persist_directory=persist_directory
    )
    vectorstore.persist()
    return vectorstore

import json
from langchain.schema import Document

def load_code_chunks():
    chunks = []
    # Load locator chunks
    locator_chunks_path = "scanner/RAG/locator_chunks.jsonl"
    with open(locator_chunks_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            # Use the usages as content, join if multiple
            usages = data.get("usages", [])
            if isinstance(usages, list):
                content = "\n".join(
                    u["code"] if isinstance(u, dict) and "code" in u else str(u)
                    for u in usages
                )
            else:
                content = str(usages)
            # Add metadata for filtering
            metadata = {
                "type": data.get("type"),
                "class_name": data.get("class_name"),
                "locator_key": data.get("locator_key"),
                "locator_value": data.get("locator_value"),
            }
            chunks.append(Document(page_content=content, metadata=metadata))
    # TODO: Add loading for step-defs, POMs, core patterns, etc.
    return chunks

if __name__ == "__main__":
    chunks = load_code_chunks()
    vectorstore = build_vectorstore(chunks)
    print("Vectorstore built and persisted.")