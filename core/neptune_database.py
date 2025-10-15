import os
import boto3
from gremlin_python.driver import client, serializer
from gremlin_python.driver.auth import AwsSigV4Auth
from typing import List, Dict, Any

from core.database import GraphDBInterface, KnowledgeGraph
from core.config import settings

class NeptuneDatabase(GraphDBInterface):
    """
    Concrete implementation of the GraphDBInterface for AWS Neptune,
    updated to use secure, passwordless IAM authentication.
    """
    def __init__(self):
        # 1. Create a boto3 session to interact with AWS
        # It will automatically use the credentials from your environment
        session = boto3.Session()
        
        # 2. Get the AWS region from the Neptune endpoint URL
        region = settings.NEPTUNE_ENDPOINT.split('.')[2]

        # 3. Use AwsSigV4Auth to handle the secure authentication handshake
        aws_auth = AwsSigV4Auth(
            aws_access_key_id=session.get_credentials().access_key,
            aws_secret_access_key=session.get_credentials().secret_key,
            aws_session_token=session.get_credentials().token,
            aws_region=region,
        )

        # 4. Initialize the client with the IAM authenticator
        self._client = client.Client(
            settings.NEPTUNE_ENDPOINT,
            'g',
            auth=aws_auth,
            message_serializer=serializer.GraphSONSerializersV2d0()
        )
        print("Successfully configured Neptune client with IAM Authentication.")


    def write_graph(self, graph: KnowledgeGraph):
        """Writes a KnowledgeGraph object to Neptune using Gremlin queries."""
        for node in graph.nodes:
            query = (
                f"g.V().has('id', '{node.id}').fold()"
                f".coalesce(unfold(), "
                f"addV('{node.type}').property('id', '{node.id}'))"
            )
            self._execute_gremlin_query(query)

        for edge in graph.edges:
            query = (
                f"g.V().has('id', '{edge.source}').as('a')"
                f".V().has('id', '{edge.target}').as('b')"
                f".coalesce(__.inE('{edge.label}').where(outV().as('a')),"
                f"addE('{edge.label}').from('a').to('b'))"
            )
            self._execute_gremlin_query(query)

    def execute_query(self, query: str, params: Dict = None) -> List[Dict[str, Any]]:
        """Executes a Gremlin query."""
        return self._execute_gremlin_query(query)

    def _execute_gremlin_query(self, query: str) -> List[Dict[str, Any]]:
        """Helper function to run a Gremlin query and get results."""
        callback = self._client.submitAsync(query)
        results = callback.result().all().result()
        return results

    def ensure_vector_index(self, index_name: str, node_label: str, property_name: str, dimensions: int):
        print(f"NOTE: Vector index '{index_name}' in Neptune requires configuration with an external service like OpenSearch.")
        pass

    def find_similar_node(self, index_name: str, node_embedding: List[float], similarity_threshold: float) -> Dict[str, Any] | None:
        print("NOTE: Vector search in Neptune requires an integrated vector database.")
        return None

    def close(self):
        self._client.close()