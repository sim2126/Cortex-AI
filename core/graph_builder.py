# /core/graph_builder.py
print("--- RUNNING FIXED VERSION WITH CORRECTED IMPORT ---")
import os
from dotenv import load_dotenv
import requests
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from core.models import Node, Edge, KnowledgeGraph, Ontology
from core.database import Neo4jDatabase
from core.entity_resolver import EntityResolver
from core.config import settings

def get_latest_ontology() -> Ontology:
    """Fetches the latest ontology from our API service."""
    print("--- Fetching Latest Ontology from Service ---")
    try:
        response = requests.get("http://127.0.0.1:8000/ontology/")
        response.raise_for_status()
        
        ontology_data = response.json()['ontology']
        ontology = Ontology(**ontology_data)
        
        print(f"Node Types: {ontology.node_types}")
        print(f"Edge Labels: {ontology.edge_labels}")
        print("---------------------------------------")
        return ontology
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch ontology from the API. Is the API server running?")
        print(f"Details: {e}")
        raise

def get_graph_extraction_chain(llm, ontology: Ontology):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an expert at extracting information from text and structuring it as a knowledge graph.
        You must adhere strictly to the provided ontology. Only extract entities and relationships
        that conform to the allowed types and labels.

        --- ONTOLOGY ---
        Allowed Node Types: {node_types}
        Allowed Edge Labels: {edge_labels}
        ---

        - For each node, you MUST provide its 'id' and 'type'.
        - For each edge, you MUST provide the 'source', 'target', and 'label'.
        """),
        ("human", "Extract the knowledge graph from the following text:\n\n---\n{text}\n---")
    ])
    formatted_prompt = prompt.partial(
        node_types=", ".join(ontology.node_types),
        edge_labels=", ".join(ontology.edge_labels)
    )
    return formatted_prompt | llm.with_structured_output(KnowledgeGraph)

def extract_and_embed_graph(text: str, llm, embeddings_model, ontology: Ontology) -> KnowledgeGraph:
    print("\n--- Extracting and Embedding Raw Knowledge Graph ---")
    extraction_chain = get_graph_extraction_chain(llm, ontology)
    graph = extraction_chain.invoke({"text": text})
    node_texts = [f"Entity: {node.id}, Type: {node.type}" for node in graph.nodes]
    if node_texts:
        embeddings = embeddings_model.embed_documents(node_texts)
        for i, node in enumerate(graph.nodes):
            node.embedding = embeddings[i]
    return graph

if __name__ == '__main__':
    load_dotenv()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)
    
    sample_text = """
    Meta Platforms, Inc., led by its CEO Mark Zuckerberg, is an American multinational technology
    conglomerate based in Menlo Park. The company, which was founded by Zuckerberg at Harvard,
    owns Facebook, Instagram, and WhatsApp.
    """
    
    db_client = Neo4jDatabase()
    
    try:
        resolver = EntityResolver(db_client, embeddings_model)
        ontology = get_latest_ontology()
        raw_graph = extract_and_embed_graph(sample_text, llm, embeddings_model, ontology)
        
        if raw_graph and raw_graph.nodes:
            resolved_graph = resolver.resolve_and_merge_graph(raw_graph)
            print("\nWriting clean, resolved graph to the database...")
            db_client.write_graph(resolved_graph)
            print("Graph data successfully written.")
            print("---------------------------------")
        else:
            print("No graph data was extracted from the text.")
            
    finally:
        db_client.close()
        print("Database connection closed.")