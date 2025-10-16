# /core/database.py

from abc import ABC, abstractmethod
import os
from neo4j import GraphDatabase
from typing import List, Dict, Any

from core.models import KnowledgeGraph

class GraphDBInterface(ABC):
    """
    An abstract base class defining the standard interface for interacting with a graph database.
    """
    @abstractmethod
    def write_graph(self, graph: KnowledgeGraph):
        pass

    @abstractmethod
    def execute_query(self, query: str, params: Dict = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def ensure_vector_index(self, index_name: str, node_label: str, property_name: str, dimensions: int):
        pass

    @abstractmethod
    def find_similar_node(self, index_name: str, node_embedding: List[float], similarity_threshold: float) -> Dict[str, Any] | None:
        pass
    
    @abstractmethod
    def close(self):
        pass


class Neo4jDatabase(GraphDBInterface):
    """Concrete implementation of the GraphDBInterface for Neo4j."""
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        if not all([uri, user, password]):
            raise ValueError("Neo4j credentials not found in .env file.")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def write_graph(self, graph: KnowledgeGraph):
        """
        Writes a knowledge graph to the database, correctly applying dynamic labels.
        """
        with self._driver.session() as session:
            for node in graph.nodes:
                cypher = f"""
                MERGE (n:`{node.type}` {{id: $id}})
                ON CREATE SET n.embedding = $embedding
                SET n += {{type: $type}}
                SET n:Entity
                """
                session.run(
                    cypher,
                    id=node.id, type=node.type, embedding=node.embedding
                )
            for edge in graph.edges:
                cypher = f"""
                MATCH (a {{id: $source}})
                MATCH (b {{id: $target}})
                MERGE (a)-[r:`{edge.label}`]->(b)
                """
                session.run(
                    cypher,
                    source=edge.source, target=edge.target
                )

    def execute_query(self, query: str, params: Dict = None) -> List[Dict[str, Any]]:
        with self._driver.session() as session:
            result = session.run(query, params or {})
            return result.data()

    def ensure_vector_index(self, index_name: str, node_label: str, property_name: str, dimensions: int):
        with self._driver.session() as session:
            session.run(f"""
            CREATE VECTOR INDEX `{index_name}` IF NOT EXISTS
            FOR (n:{node_label}) ON (n.{property_name})
            OPTIONS {{ indexConfig: {{
                `vector.dimensions`: {dimensions},
                `vector.similarity_function`: 'cosine'
            }}}}
            """)
        print(f"Neo4j vector index '{index_name}' ensured.")

    def find_similar_node(self, index_name: str, node_embedding: List[float], similarity_threshold: float) -> Dict[str, Any] | None:
        query = """
        CALL db.index.vector.queryNodes($index_name, 1, $embedding)
        YIELD node, score
        WHERE score >= $threshold
        RETURN node.id AS id, node.type AS type, score
        """
        params = {
            "index_name": index_name,
            "embedding": node_embedding,
            "threshold": similarity_threshold
        }
        with self._driver.session() as session:
            result = session.run(query, params)
            return result.single()

    def close(self):
        self._driver.close()
