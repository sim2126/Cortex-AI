from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from core.retriever import query_vector_store
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# --- Pydantic Models for a more robust planner ---
class RAGPlan(BaseModel):
    """The plan for executing a request."""
    query_type: Literal["conversational", "informational"] = Field(
        description="The classification of the user's query: either 'conversational' (a greeting, thank you, etc.) or 'informational' (a question seeking knowledge)."
    )
    search_query: str = Field(
        description="For 'informational' queries, a concise, keyword-focused query optimized for vector database retrieval. For 'conversational' queries, this can be an empty string."
    )

# --- Agent State ---
class AgentState(TypedDict):
    question: str
    search_query: str
    context: str
    answer: str

# --- Agent Nodes (Final Version with Conversational Check) ---

def query_planner(state: AgentState):
    """
    The new entry point. It first classifies the user's intent.
    If conversational, it provides a direct answer.
    If informational, it creates an optimized search query.
    """
    logger.info("--- QUERY PLANNER: Classifying intent and generating search query ---")
    
    llm = ChatGoogleGenerativeAI(model=settings.FAST_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an expert at classifying user intent and optimizing queries.
        First, determine if the user's input is 'conversational' (like 'hello', 'thank you') or 'informational' (a question).
        
        - If 'conversational', set query_type to 'conversational' and search_query to an empty string.
        - If 'informational', set query_type to 'informational' and generate a concise search query based on the user's question.
        """),
        ("human", "User Input: {question}")
    ])
    
    chain = prompt | llm.with_structured_output(RAGPlan)
    result = chain.invoke({"question": state['question']})
    
    if result.query_type == "conversational":
        logger.info("  - Intent: Conversational. Responding directly.")
        # For a conversational query, we set the answer directly and skip the RAG pipeline.
        return {
            "answer": "Hello! I'm Cortex, your personal RAG agent. You can ask me questions about the documents you've uploaded."
        }
    
    logger.info(f"  - Intent: Informational. Optimized Search Query: {result.search_query}")
    return {"search_query": result.search_query}

def retrieve_context(state: AgentState):
    """
    Retrieves relevant context from the vector store using the optimized search query.
    """
    logger.info("--- RETRIEVER: Fetching context from vector store ---")
    
    results = query_vector_store(state['search_query'])
    if not results:
        logger.warning("  - No context found in vector store.")
        return {"context": ""}
    
    context = "\n\n---\n\n".join([doc.page_content for doc in results])
    logger.info(f"  - Retrieved context (first 200 chars): {context[:200]}...")
    return {"context": context}

def generate_response(state: AgentState):
    """
    Generates a final answer, strictly adhering to the provided context.
    """
    logger.info("--- RESPONDER: Generating final answer ---")
    
    llm = ChatGoogleGenerativeAI(model=settings.GENERATION_MODEL, temperature=0.1)
    
    prompt_template = """
    You are Cortex AI, a helpful AI assistant. Your task is to provide a detailed and well-structured answer to the user's question based *only* on the context provided below.

    **Strict Rules:**
    1.  Adhere exclusively to the provided context. Do not use any external knowledge.
    2.  If the context has enough information, synthesize a comprehensive answer.
    3.  If the context is empty or insufficient, you MUST respond with the following exact phrase:
        "Currently, I can only help with the documents you have uploaded or the web links you have provided. Please ingest a relevant source to answer this question."

    **Context from Knowledge Base:**
    ---
    {context}
    ---

    **User's Question:** {question}

    **Comprehensive Answer:**
    """
    
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    
    answer = chain.invoke({
        "question": state['question'],
        "context": state['context']
    })
    
    logger.info(f"  - Generated Answer: {answer}")
    return {"answer": answer}

# --- Conditional Edge ---
def decide_to_retrieve(state: AgentState):
    """
    Decides whether to proceed with context retrieval or to end the process.
    If the planner set an answer directly (for conversational queries), we end.
    """
    if "answer" in state and state["answer"]:
        return "end"
    else:
        return "continue"

# --- Build and Compile the Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("planner", query_planner)
workflow.add_node("retriever", retrieve_context)
workflow.add_node("responder", generate_response)

workflow.set_entry_point("planner")

# New conditional routing after the planner
workflow.add_conditional_edges(
    "planner",
    decide_to_retrieve,
    {
        "continue": "retriever",
        "end": END
    }
)

workflow.add_edge("retriever", "responder")
workflow.set_finish_point("responder")

app = workflow.compile()

