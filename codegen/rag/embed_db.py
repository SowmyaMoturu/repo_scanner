import os
import json
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document

RAG_CHUNKS_PATH = "codegen/output/RAG/rag_chunks.jsonl"
VECTORSTORE_DIR = "codegen/output/RAG/vectorstore"


def clean_metadata(metadata):
    clean = {}
    for k, v in metadata.items():
        if isinstance(v, (list, dict)):
            clean[k] = json.dumps(v, ensure_ascii=False)
        else:
            clean[k] = v
    return clean

def load_rag_chunks(path):
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            content = data.get("code") or data.get("text") or json.dumps(data)
            metadata = {k: v for k, v in data.items() if k != "code" and k != "text"}
            metadata = clean_metadata(metadata)
            docs.append(Document(page_content=content, metadata=metadata))
    return docs

def build_vectorstore(docs, persist_directory=VECTORSTORE_DIR):
    embedding = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(
        docs,
        embedding,
        persist_directory=persist_directory
    )
    vectorstore.persist()
    print(f"Vectorstore built and persisted at: {persist_directory}")

if __name__ == "__main__":
    if not os.path.exists(RAG_CHUNKS_PATH):
        print(f"Chunks file not found: {RAG_CHUNKS_PATH}")
    else:
        docs = load_rag_chunks(RAG_CHUNKS_PATH)
        print(f"Loaded {len(docs)} chunks from {RAG_CHUNKS_PATH}")
        build_vectorstore(docs)