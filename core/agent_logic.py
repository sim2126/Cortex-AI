from typing import TypedDict, List, Tuple, Literal, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
import json

from core.retriever import query_vector_store, query_knowledge_graph, Filter
from core.router import get_router_chain
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)

# --- Pydantic Models for Structured LLM Calls ---
class Grade(BaseModel):
    """A model for grading the sufficiency of a generated answer."""
    is_sufficient: bool = Field(description="True if the answer directly and completely addresses the user's question. False otherwise.")
    reasoning: str = Field(description="A brief explanation of why the answer is or is not sufficient.")

class DecomposedQuery(BaseModel):
    """Represents a multi-step query plan."""
    sub_queries: List[str] = Field(description="A list of sub-queries to execute in sequence.")
    dependencies: List[int] = Field(description="A list where dependencies[i] is the index of the sub_query that sub_query[i] depends on, or -1 if it has no dependency.")

# --- Enhanced Agent State ---
class AgentState(TypedDict):
    question: str
    plan: str
    sub_query_results: List[Any]
    current_sub_query_index: int
    answer: str
    # Streamed output for the client
    streaming_thought: str

# --- Agent Nodes (Upgraded and New) ---

def planner(state: AgentState):
    """
    The entry point of the agent. Decomposes the query into a multi-step plan if necessary.
    """
    logger.info("--- PLANNER: Creating execution plan ---")
    yield {"streaming_thought": "Analyzing the query and forming a plan..."}
    
    llm = ChatGoogleGenerativeAI(model=settings.FAST_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an expert query planner. Your task is to decompose a complex user query into a series of simpler, executable sub-queries.
        - If the query is simple and can be answered in one step, return a single sub-query.
        - If the query requires multiple steps (e.g., finding X, then using X to find Y), break it down.
        - Define dependencies. For "What companies were founded by people who attended Harvard?", the plan should be:
          1. "Find people who attended Harvard."
          2. "Find companies founded by the people from step 1."
          The dependency for query 2 would be 0.

        Return a structured plan.
        """),
        ("human", "User Question: {question}")
    ])
    
    chain = prompt | llm.with_structured_output(DecomposedQuery)
    result = chain.invoke({"question": state['question']})
    
    plan_str = "\n".join(f"{i+1}. {q}" for i, q in enumerate(result.sub_queries))
    logger.info(f"  - Plan:\n{plan_str}")
    
    yield {
        "plan": json.dumps({"sub_queries": result.sub_queries, "dependencies": result.dependencies}),
        "current_sub_query_index": 0,
        "sub_query_results": [None] * len(result.sub_queries),
        "streaming_thought": f"I have formulated a plan:\n{plan_str}"
    }

# In core/agent_logic.py, replace the existing execute_tool function with this one.

def execute_tool(state: AgentState):
    """
    Routes and executes the current sub-query with more robust logic.
    """
    plan = json.loads(state["plan"])
    index = state["current_sub_query_index"]
    query = plan["sub_queries"][index]
    
    dependency_index = plan["dependencies"][index]
    if dependency_index != -1:
        previous_result = state["sub_query_results"][dependency_index]
        query = f"{query} (Context: {previous_result})"
        
    yield {"streaming_thought": f"Executing step {index + 1}: {query}"}
    
    router = get_router_chain()
    route = router.invoke({"question": query})
    datasource = route.datasource.lower() # Convert to lowercase for safety
    
    tool_output = ""
    # --- THIS IS THE ROBUST LOGIC ---
    # We now check if the keyword is 'in' the datasource string.
    if 'vectorstore' in datasource:
        yield {"streaming_thought": "Decision: Performing vector search."}
        results = query_vector_store(query)
        tool_output = "\n\n".join([doc.page_content for doc in results])
    elif 'graph' in datasource:
        yield {"streaming_thought": "Decision: Querying knowledge graph."}
        results, _ = query_knowledge_graph(query)
        tool_output = ", ".join([str(list(row.values())[0]) for row in results if row and row.values()])
    elif 'logical_filter' in datasource:
        yield {"streaming_thought": "Decision: Applying logical filter."}
        results, _ = query_knowledge_graph(query, filter_model=route.filter)
        tool_output = ", ".join([str(list(row.values())[0]) for row in results if row and row.values()])
    else:
        # Fallback if the router gives an unexpected output
        yield {"streaming_thought": "Warning: Router gave an unknown datasource. Defaulting to vector search."}
        results = query_vector_store(query)
        tool_output = "\n\n".join([doc.page_content for doc in results])

    current_results = state["sub_query_results"]
    current_results[index] = tool_output
    
    yield {
        "sub_query_results": current_results,
        "streaming_thought": f"Step {index + 1} complete. Found: {tool_output[:200]}..."
    }

def generate_response(state: AgentState):
    """The final step: synthesize an answer from the collected results."""
    yield {"streaming_thought": "All steps are complete. Synthesizing the final answer..."}
    
    llm = ChatGoogleGenerativeAI(model=settings.GENERATION_MODEL, temperature=0)
    prompt_template = """
    You are Cortex AI. Synthesize a clear and direct answer to the user's original question based ONLY on the context from the executed steps.
    
    Original Question: {question}

    Context from Executed Steps:
    ---
    {context}
    ---

    Based *only* on the context above, provide a direct answer to the question.
    """
    
    context = "\n".join([f"Step {i+1} Result: {res}" for i, res in enumerate(state['sub_query_results'])])
    
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": state['question'], "context": context})
    yield {"answer": answer, "streaming_thought": "Done."}

def should_continue_planning(state: AgentState):
    plan = json.loads(state["plan"])
    current_index = state["current_sub_query_index"]
    if current_index + 1 < len(plan["sub_queries"]):
        return "continue"
    else:
        return "end"

def advance_to_next_step(state: AgentState):
    """Advances the index to the next sub-query."""
    current_index = state.get("current_sub_query_index", 0)
    return {"current_sub_query_index": current_index + 1}


# --- Build and Compile the Graph ---
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("advance_step", advance_to_next_step)
workflow.add_node("responder", generate_response)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "execute_tool")
workflow.add_edge("advance_step", "execute_tool")
workflow.add_conditional_edges(
    "execute_tool",
    should_continue_planning,
    {"continue": "advance_step", "end": "responder"}
)
workflow.add_edge("responder", END)

app = workflow.compile()