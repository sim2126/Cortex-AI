import os
from neo4j import GraphDatabase
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import List, Dict, Any

# --- Constants ---
SIMILARITY_THRESHOLD = 0.90 # Cosine similarity threshold for merging entities

from core.database import GraphDBInterface # Import the interface

class EntityResolver:
    def __init__(self, db_client: GraphDBInterface, embeddings_model): # Expects any class that implements the interface
        self.db_client = db_client
        self.embeddings_model = embeddings_model
        self.db_client.ensure_vector_index(
            index_name='entity_embeddings',
            node_label='Entity',
            property_name='embedding',
            dimensions=768 # Gemini embedding dimensions
        )

    def find_similar_node(self, node_embedding: List[float]) -> Dict[str, Any] | None:
        return self.db_client.find_similar_node(
            index_name='entity_embeddings',
            node_embedding=node_embedding,
            similarity_threshold=SIMILARITY_THRESHOLD
        )

    def resolve_and_merge_graph(self, graph):
        """
        The main function that orchestrates the entity resolution process for an entire graph.
        It iterates through nodes, finds duplicates, and merges them.

        Args:
            graph: The KnowledgeGraph object to be deduplicated.

        Returns:
            A new, deduplicated KnowledgeGraph object.
        """
        print("\n--- Starting Entity Resolution and Deduplication ---")
        resolved_graph = graph.copy(deep=True)
        id_map = {} # Maps old, duplicate IDs to their new, canonical IDs

        nodes_to_keep = []
        processed_ids = set()

        for node in resolved_graph.nodes:
            if node.id in processed_ids:
                continue

            similar_node = self.find_similar_node(node.embedding)
            
            if similar_node and similar_node['id'] != node.id:
                canonical_id = similar_node['id']
                print(f"  - Found duplicate: '{node.id}' is similar to existing node '{canonical_id}'. Merging.")
                id_map[node.id] = canonical_id
            else:
                # This is a new, unique node. We will keep it.
                nodes_to_keep.append(node)
                processed_ids.add(node.id)

        # Update graph structure based on the id_map
        resolved_graph.nodes = nodes_to_keep
        
        for edge in resolved_graph.edges:
            if edge.source in id_map:
                edge.source = id_map[edge.source]
            if edge.target in id_map:
                edge.target = id_map[edge.target]
        
        # Remove self-referencing loops that may have been created by the merge
        resolved_graph.edges = [edge for edge in resolved_graph.edges if edge.source != edge.target]
        
        print("--- Entity Resolution Complete ---")
        return resolved_graph