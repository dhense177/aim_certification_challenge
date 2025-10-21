from langchain_community.document_loaders import DirectoryLoader, UnstructuredPDFLoader
from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from operator import itemgetter
from pydantic import BaseModel, Field
from typing import Optional
from langchain.chains import RetrievalQA
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.storage import InMemoryStore
from langchain.retrievers import ParentDocumentRetriever
import os
from dotenv import load_dotenv
load_dotenv()

RAG_TEMPLATE = """\
You are a helpful and kind assistant. Use the context provided below to answer the question.

If you do not know the answer, or are unsure, say you don't know.

Query:
{question}

Context:
{context}
"""

EMBEDDINGS = OpenAIEmbeddings(model="text-embedding-3-small")
CHAT_MODEL = ChatOpenAI(model="gpt-4.1-nano")
LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
COLLECTION_NAME = "solar_docs"

def load_docs(path, municipality_name):
    loader = DirectoryLoader(path, glob="*.pdf", loader_cls=UnstructuredPDFLoader)
    docs = loader.load()
    for doc in docs:
        doc.metadata["municipality"] = municipality_name
    return docs


def build_or_load_vectorstore():
    # Load documents from all available municipalities
    municipalities = ["ashburnham", "barre", "berlin"]
    # municipalities = ["barre"]
    all_documents = []
    
    for municipality in municipalities:
        path = f"extracted_data/mass_municipalities/{municipality}/"
        if os.path.exists(path):
            documents = load_docs(path, municipality)
            all_documents.extend(documents)

    # all_documents = load_docs("extracted_data/mass_municipalities/barre/", "barre")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_documents)

    # Create vectorstore with documents
    vectorstore = Qdrant.from_documents(
        documents=chunks,
        embedding=EMBEDDINGS,
        location=":memory:",
        collection_name=COLLECTION_NAME,
    )

    return vectorstore



def get_qa_chain():

    vectorstore = build_or_load_vectorstore()
    naive_retriever = vectorstore.as_retriever(search_kwargs={"k" : 10})
    rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
    naive_retrieval_chain = (

        {"context": itemgetter("question") | naive_retriever, "question": itemgetter("question")}

        | RunnablePassthrough.assign(context=itemgetter("context"))

        | {"response": rag_prompt | CHAT_MODEL, "context": itemgetter("context")}
    )

    # return RetrievalQA.from_chain_type(llm=LLM, retriever=naive_retriever)
    return naive_retrieval_chain




def get_qa_chain_advanced():
    municipalities = ["ashburnham", "barre", "berlin"]
    # municipalities = ["barre"]
    parent_docs = []
    
    for municipality in municipalities:
        path = f"extracted_data/mass_municipalities/{municipality}/"
        if os.path.exists(path):
            documents = load_docs(path, municipality)
            parent_docs.extend(documents)
    # parent_docs = load_docs("extracted_data/mass_municipalities/barre/", "barre")
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)


    client = QdrantClient(location=":memory:")

    client.create_collection(
        collection_name="full_documents",
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
    )

    parent_document_vectorstore = QdrantVectorStore(
        collection_name="full_documents", embedding=OpenAIEmbeddings(model="text-embedding-3-small"), client=client
    )

    store = InMemoryStore()

    parent_document_retriever = ParentDocumentRetriever(
        vectorstore = parent_document_vectorstore,
        docstore=store,
        child_splitter=child_splitter,
    )

    parent_document_retriever.add_documents(parent_docs, ids=None)
    rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
    parent_document_retrieval_chain = (
    {"context": itemgetter("question") | parent_document_retriever, "question": itemgetter("question")}
    | RunnablePassthrough.assign(context=itemgetter("context"))
    | {"response": rag_prompt | CHAT_MODEL, "context": itemgetter("context")}
    )
    return parent_document_retrieval_chain
    # naive_retriever = vectorstore.as_retriever(search_kwargs={"k" : 10})
    # rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
    # naive_retrieval_chain = (

    #     {"context": itemgetter("question") | naive_retriever, "question": itemgetter("question")}

    #     | RunnablePassthrough.assign(context=itemgetter("context"))

    #     | {"response": rag_prompt | CHAT_MODEL, "context": itemgetter("context")}
    # )

    # # return RetrievalQA.from_chain_type(llm=LLM, retriever=naive_retriever)
    # return naive_retrieval_chain

