# /core/retriever.py

import os
import re
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from typing import List
from neo4j import GraphDatabase
from core.config import settings

VECTOR_STORE_PATH = "vector_store"

class Filter(BaseModel):
    node_type: str = Field(description="The type of the node to filter on (e.g., 'Company', 'Person').")
    property: str = Field(description="The property of the node to filter on (e.g., 'location', 'name').")
    value: str = Field(description="The value to filter for.")

def query_vector_store(query: str, k: int = 3):
    embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)
    vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings_model, allow_dangerous_deserialization=True)
    return vector_store.similarity_search(query, k=k)

def get_graph_schema():
    uri = os.getenv("NEO4J_URI", settings.NEO4J_URI)
    user = os.getenv("NEO4J_USERNAME", settings.NEO4J_USERNAME)
    password = os.getenv("NEO4J_PASSWORD", settings.NEO4J_PASSWORD)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        node_props_query = "MATCH (n) UNWIND keys(n) AS key RETURN collect(distinct key) AS props"
        node_props_result = session.run(node_props_query).single()
        node_props = node_props_result['props'] if node_props_result else []
        
        rel_info_query = """
        CALL db.schema.visualization() YIELD relationships UNWIND relationships AS rel
        RETURN DISTINCT type(rel) AS rel_type, labels(startNode(rel)) AS source_labels, labels(endNode(rel)) AS target_labels
        """
        relationships = session.run(rel_info_query).data()
    driver.close()
    
    schema_str = f"Node Properties: {node_props}\nRelationships:\n"
    for rel in relationships:
        source_labels = [label for label in rel['source_labels'] if label != 'Entity']
        target_labels = [label for label in rel['target_labels'] if label != 'Entity']
        if source_labels and target_labels:
            schema_str += f"- (:{source_labels[0]}) -[:{rel['rel_type']}]-> (:{target_labels[0]})\n"
    return schema_str


def query_knowledge_graph(query: str, filter_model: Filter = None):
    schema = get_graph_schema()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    if filter_model:
        cypher_query = f"""
        MATCH (n:{filter_model.node_type})
        WHERE n.{filter_model.property} CONTAINS '{filter_model.value}'
        RETURN n.id AS result
        """
    else:
        # --- THIS IS THE FINAL, MOST ROBUST PROMPT ---
        # The examples now correctly use the CONTAINS operator, reinforcing the instruction.
        system_template = """
        You are a Cypher query expert. Your task is to convert a user's question into a single, executable Cypher query for a Neo4j database.

        **Strict Rules:**
        1.  **Analyze the Schema**: Use ONLY the node types, properties, and relationship types mentioned in the provided schema.
        2.  **Use `CONTAINS` for Flexibility**: When filtering on string properties like names, ALWAYS use the `CONTAINS` operator for partial matching.
        3.  **Return the `id` Property**: When returning a node's name or identifier, ALWAYS return its `id` property.
        4.  **No Explanations**: Your output must be ONLY the Cypher query. Do not include any explanations or markdown formatting like ```cypher```.

        **Examples:**
        - User Question: "Which companies does Meta own?"
        - Your Cypher Query: `MATCH (o:Organization)-[:ACQUIRED]->(c:Organization) WHERE o.id CONTAINS 'Meta' RETURN c.id AS company`

        - User Question: "Who is the CEO of Meta?"
        - Your Cypher Query: `MATCH (p:Person)-[:CEO_OF]->(o:Organization) WHERE o.id CONTAINS 'Meta' RETURN p.id AS person`

        **Schema for this request:**
        ---
        {schema}
        ---
        """
        prompt = ChatPromptTemplate.from_messages([("system", system_template), ("human", "{question}")])
        cypher_chain = prompt | llm | StrOutputParser()
        
        cypher_query = cypher_chain.invoke({"question": query, "schema": schema})
        
        cypher_query = re.sub(r'```(cypher)?', '', cypher_query, flags=re.IGNORECASE)
        cypher_query = cypher_query.strip()


    print(f"Executing Cypher: {cypher_query}")

    uri = os.getenv("NEO4J_URI", settings.NEO4J_URI)
    user = os.getenv("NEO4J_USERNAME", settings.NEO4J_USERNAME)
    password = os.getenv("NEO4J_PASSWORD", settings.NEO4J_PASSWORD)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run(cypher_query).data()
    driver.close()
    
    return result, cypher_query
