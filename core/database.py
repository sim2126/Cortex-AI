# /core/database.py

from abc import ABC, abstractmethod
import os
from neo4j import GraphDatabase
from typing import List, Dict, Any

from core.models import KnowledgeGraph

class GraphDBInterface(ABC):
    """
    An abstract base class defining the standard interface for interacting with a graph database.
    This allows for pluggable backends (e.g., Neo4j, AWS Neptune).
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
        with self._driver.session() as session:
            # Write nodes
            for node in graph.nodes:
                session.run(
                    "MERGE (n:Entity {id: $id}) SET n.type = $type, n.embedding = $embedding", 
                    id=node.id, type=node.type, embedding=node.embedding
                )
            
            # Write edges - Fixed to avoid KeyError
            for edge in graph.edges:
                # Use parameterized query with relationship type
                query = """
                MATCH (a:Entity {id: $source})
                MATCH (b:Entity {id: $target})
                CALL apoc.merge.relationship(a, $label, {}, {}, b, {})
                YIELD rel
                RETURN rel
                """
                try:
                    session.run(query, source=edge.source, target=edge.target, label=edge.label)
                except Exception as e:
                    # Fallback if APOC is not available
                    print(f"APOC not available, using alternative method for edge: {edge.label}")
                    # Escape the relationship type properly
                    safe_label = edge.label.replace('`', '')
                    fallback_query = f"""
                    MATCH (a:Entity {{id: $source}})
                    MATCH (b:Entity {{id: $target}})
                    MERGE (a)-[r:`{safe_label}`]->(b)
                    RETURN r
                    """
                    session.run(fallback_query, source=edge.source, target=edge.target)

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