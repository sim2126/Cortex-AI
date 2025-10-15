import unittest
from unittest.mock import MagicMock, patch

# Adjust the path to import from the parent directory's 'core' module
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.entity_resolver import EntityResolver, SIMILARITY_THRESHOLD
from core.graph_builder import KnowledgeGraph, Node, Edge

class TestEntityResolver(unittest.TestCase):

    def setUp(self):
        """Set up mocked components before each test."""
        # Mock the database interface. We don't want to touch the actual DB in a unit test.
        self.mock_db_client = MagicMock()
        
        # Mock the embeddings model
        self.mock_embeddings_model = MagicMock()
        
        # Instantiate the resolver with our mocked dependencies
        self.resolver = EntityResolver(self.mock_db_client, self.mock_embeddings_model)

    def test_resolve_and_merge_graph_with_duplicate(self):
        """
        Tests if the resolver correctly identifies a duplicate node,
        merges it, and updates the graph edges accordingly.
        """
        # --- Arrange ---
        
        # 1. Create a sample graph with a clear duplicate.
        #    'Zuckerberg' should be merged into 'Mark Zuckerberg'.
        raw_graph = KnowledgeGraph(
            nodes=[
                Node(id='Mark Zuckerberg', type='Person', embedding=[0.1, 0.2, 0.3]),
                Node(id='Meta Platforms, Inc.', type='Organization', embedding=[0.4, 0.5, 0.6]),
                Node(id='Zuckerberg', type='Person', embedding=[0.11, 0.21, 0.31]) # Very similar embedding
            ],
            edges=[
                Edge(source='Zuckerberg', target='Meta Platforms, Inc.', label='CEO_OF')
            ]
        )
        
        # 2. Configure the mock database's find_similar_node method.
        #    This is the critical part of the mock. We define what the mock DB "sees".
        def mock_find_similar(embedding):
            # If it gets the embedding for 'Zuckerberg', it should "find" 'Mark Zuckerberg' in the DB.
            if embedding == [0.11, 0.21, 0.31]:
                return {'id': 'Mark Zuckerberg', 'type': 'Person', 'score': SIMILARITY_THRESHOLD + 0.05}
            # For all other embeddings, it finds nothing.
            return None
            
        self.mock_db_client.find_similar_node.side_effect = mock_find_similar
        
        # --- Act ---
        
        # Run the resolver on our sample graph
        resolved_graph = self.resolver.resolve_and_merge_graph(raw_graph)
        
        # --- Assert ---
        
        # 1. Check that the duplicate node ('Zuckerberg') was removed.
        self.assertEqual(len(resolved_graph.nodes), 2, "Resolver should have removed the duplicate node.")
        
        node_ids = {node.id for node in resolved_graph.nodes}
        self.assertIn('Mark Zuckerberg', node_ids)
        self.assertIn('Meta Platforms, Inc.', node_ids)
        self.assertNotIn('Zuckerberg', node_ids, "The duplicate 'Zuckerberg' node should not be in the final list.")
        
        # 2. Check that the edge was correctly re-mapped.
        self.assertEqual(len(resolved_graph.edges), 1, "There should be exactly one edge in the resolved graph.")
        
        updated_edge = resolved_graph.edges[0]
        self.assertEqual(updated_edge.source, 'Mark Zuckerberg', "Edge source should be re-mapped to the canonical node.")
        self.assertEqual(updated_edge.target, 'Meta Platforms, Inc.')
        self.assertEqual(updated_edge.label, 'CEO_OF')


if __name__ == '__main__':
    unittest.main()