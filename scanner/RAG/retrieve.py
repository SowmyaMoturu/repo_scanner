from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

def load_vectorstore(persist_directory="vectorstore"):
    embedding = OpenAIEmbeddings()
    return Chroma(persist_directory=persist_directory, embedding_function=embedding)

def retrieve_code_context(query, vectorstore, k=5, filter_metadata=None):
    if filter_metadata:
        docs = vectorstore.similarity_search(query, k=k, filter=filter_metadata)
    else:
        docs = vectorstore.similarity_search(query, k=k)
    return docs

def extract_class_names_from_docs(docs):
    """Extract unique class names from retrieved docs' metadata."""
    class_names = set()
    for doc in docs:
        class_name = doc.metadata.get("class_name")
        if class_name:
            class_names.add(class_name)
    return list(class_names)

def retrieve_chain_for_user_story(user_story, vectorstore, k=3):
    # 1. Retrieve relevant step-definitions
    stepdef_docs = retrieve_code_context(user_story, vectorstore, k=k, filter_metadata={"type": "stepdef"})
    
    # 2. Extract class names from step-defs (if available)
    class_names = extract_class_names_from_docs(stepdef_docs)
    pom_docs = []
    locator_docs = []
    # 3. For each class, retrieve POM methods and locators
    for class_name in class_names:
        pom_docs.extend(retrieve_code_context(user_story, vectorstore, k=k, filter_metadata={"type": "pom_method", "class_name": class_name}))
        locator_docs.extend(retrieve_code_context(user_story, vectorstore, k=k, filter_metadata={"type": "locator", "class_name": class_name}))
    # Optionally, if no class_name found, do a general search
    if not class_names:
        pom_docs = retrieve_code_context(user_story, vectorstore, k=k, filter_metadata={"type": "pom_method"})
        locator_docs = retrieve_code_context(user_story, vectorstore, k=k, filter_metadata={"type": "locator"})
    # 4. Combine and deduplicate
    all_docs = stepdef_docs + pom_docs + locator_docs
    seen = set()
    unique_docs = []
    for doc in all_docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)
    return unique_docs

if __name__ == "__main__":
    vectorstore = load_vectorstore()
    user_story = "As a user, I want to log in with my email and password"
    docs = retrieve_chain_for_user_story(user_story, vectorstore, k=3)
    for doc in docs:
        print(doc.metadata, "\n", doc.page_content, "\n---")