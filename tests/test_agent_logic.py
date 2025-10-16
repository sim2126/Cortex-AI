# /tests/test_agent_logic.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add root directory to path to allow imports from 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agent_logic import app as cortex_ai_agent, AgentState

class TestAgentLogic(unittest.TestCase):

    @patch('core.agent_logic.get_router_chain')
    @patch('core.agent_logic.query_vector_store')
    @patch('core.agent_logic.query_knowledge_graph')
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    def test_full_graph_query_flow(
        self,
        mock_chat_google,
        mock_query_kg,
        mock_query_vs,
        mock_get_router
    ):
        """
        Tests the full agent flow for a question that should be routed to the knowledge graph.
        """
        # --- Arrange ---

        # 1. Mock the router to always choose the 'graph' tool
        mock_router_response = MagicMock()
        mock_router_response.datasource = 'graph'
        mock_router_chain = MagicMock()
        mock_router_chain.invoke.return_value = mock_router_response
        mock_get_router.return_value = mock_router_chain

        # 2. Mock the knowledge graph to return a specific result
        mock_kg_result = ([{'company': 'Instagram'}, {'company': 'WhatsApp'}], "MATCH (n) RETURN n")
        mock_query_kg.return_value = mock_kg_result
        
        # 3. Mock the final response generation LLM
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_llm_instance # for planner
        
        # Mocking the planner's structured output
        mock_plan = MagicMock()
        mock_plan.query_type = "informational"
        mock_plan.plan = "Route to the appropriate tool."

        
        # Mocking the final answer generation
        final_answer_chain = MagicMock()
        final_answer_chain.invoke.return_value = "Based on the knowledge graph, Meta owns Instagram and WhatsApp."
        
        # Mocking the grader
        mock_grade = MagicMock()
        mock_grade.is_sufficient = True
        
        # This function will return different mocks depending on the input
        def llm_side_effect(*args, **kwargs):
            if 'with_structured_output' in str(args) or 'with_structured_output' in str(kwargs):
                if 'Grade' in str(kwargs):
                    return mock_grade
                return mock_plan
            return final_answer_chain
            
        mock_chat_google.return_value.with_structured_output.side_effect = llm_side_effect
        mock_chat_google.return_value.invoke.return_value = "Based on the knowledge graph, Meta owns Instagram and WhatsApp."


        # --- Act ---
        
        # Define the initial state for the agent
        inputs = {"question": "What companies does Meta own?"}
        
        # Run the agent
        final_state = cortex_ai_agent.invoke(inputs)

        # --- Assert ---
        
        # Verify that the router was called correctly
        mock_get_router.return_value.invoke.assert_called_with({"question": inputs["question"]})
        
        # Verify that the knowledge graph was queried (and the vector store was not)
        mock_query_kg.assert_called_once_with(inputs["question"])
        mock_query_vs.assert_not_called()
        
        # Verify the final answer is what we expect
        self.assertIn("Instagram", final_state["answer"])
        self.assertIn("WhatsApp", final_state["answer"])
        self.assertEqual(final_state["datasource"], "graph")

if __name__ == '__main__':
    unittest.main()