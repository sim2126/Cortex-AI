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

# --- Pydantic model for the filter ---
class Filter(BaseModel):
    """A filter to apply to a knowledge graph query."""
    node_type: str = Field(description="The type of the node to filter on (e.g., 'Company', 'Person').")
    property: str = Field(description="The property of the node to filter on (e.g., 'location', 'name').")
    value: str = Field(description="The value to filter for.")

def query_vector_store(query: str, k: int = 3):
    embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)
    vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings_model, allow_dangerous_deserialization=True)
    return vector_store.similarity_search(query, k=k)

def get_graph_schema():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        node_props_query = "MATCH (n) UNWIND keys(n) AS key RETURN collect(distinct key) AS props"
        node_props = session.run(node_props_query).single()['props']
        rel_info_query = """
        CALL db.schema.visualization() YIELD relationships UNWIND relationships AS rel
        RETURN DISTINCT type(rel) AS rel_type, labels(startNode(rel)) AS source_labels, labels(endNode(rel)) AS target_labels
        """
        relationships = session.run(rel_info_query).data()
    driver.close()
    
    schema_str = f"Node Properties: {node_props}\nRelationships:\n"
    for rel in relationships:
        schema_str += f"- (:{(rel['source_labels'])}) -[:{rel['rel_type']}]-> (:{(rel['target_labels'])})\n"
    return schema_str

def query_knowledge_graph(query: str, filter_model: Filter = None):
    """
    Queries the knowledge graph, optionally applying a logical filter.
    """
    schema = get_graph_schema()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    if filter_model:
        # If a filter is provided, construct a direct Cypher query
        cypher_query = f"""
        MATCH (n:{filter_model.node_type})
        WHERE n.{filter_model.property} CONTAINS '{filter_model.value}'
        RETURN n.id AS result
        """
    else:
        # Otherwise, use the LLM to generate the query
        system_template = """
        You are an expert at converting user questions into Cypher queries based on the provided graph schema.
        You must use only the schema provided.

        --- IMPORTANT ---
        - When filtering on a node's name, you MUST use the 'id' property and the `CONTAINS` operator for flexible matching. (e.g., `WHERE n.id CONTAINS 'Meta'`)
        - When returning a node's name, you MUST return its 'id' property. (e.g., `RETURN n.id AS name`)
        ---

        Your output must be a single, executable Cypher query. Do not include any explanations or markdown formatting.
        
        Schema:
        ---
        {schema}
        ---
        """
        prompt = ChatPromptTemplate.from_messages([("system", system_template), ("human", "{question}")])
        cypher_chain = prompt | llm | StrOutputParser()
        
        cypher_query = cypher_chain.invoke({"question": query, "schema": schema})
        
        match = re.search(r"```(cypher)?(.*)```", cypher_query, re.DOTALL)
        if match:
            cypher_query = match.group(2).strip()

    print(f"Executing Cypher: {cypher_query}")

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run(cypher_query).data()
    driver.close()
    
    return result, cypher_query