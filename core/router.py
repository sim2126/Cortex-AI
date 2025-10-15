from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from core.retriever import Filter # Import the new Filter model

class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: Literal["vectorstore", "graph", "logical_filter"] = Field(
        ...,
        description="Given a user question, route it to the most relevant datasource."
    )
    # The filter is now part of the routing decision
    filter: Filter = Field(
        None,
        description="The filter to apply if the datasource is 'logical_filter'."
    )

def get_router_chain():
    """Creates an LLM chain that routes a query to the appropriate tool."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_llm = llm.with_structured_output(RouteQuery)
    system_prompt = """
    You are an expert at routing a user question to the appropriate data source.

    - Use 'vectorstore' for semantic searches, definitions, or general information.
      Example: 'What is a neural network?'
    
    - Use 'graph' for questions about relationships, connections, or multi-hop reasoning.
      Example: 'What companies did Mark Zuckerberg found?'
      
    - Use 'logical_filter' for questions that require filtering by a specific property or attribute.
      This is for precise lookups, not for semantic understanding.
      Example: 'Which companies are located in Menlo Park?' or 'Find a person named John Doe'.
      If you choose 'logical_filter', you MUST provide the node type, property, and value for the filter.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])
    return prompt | structured_llm