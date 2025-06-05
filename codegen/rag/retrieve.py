from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

VECTORSTORE_DIR = "codegen/output/RAG/vectorstore"

def retrieve_similar_chunks(query, k=5):
    embedding = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=embedding)
    docs = vectorstore.similarity_search(query, k=k)
    # Return as list of dicts for easy display
    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]