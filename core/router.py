from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from core.retriever import Filter

class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: Literal["vectorstore", "graph", "logical_filter"] = Field(
        ...,
        description="The single, most relevant data source for the user's query."
    )
    filter: Filter = Field(
        None,
        description="The filter to apply if the datasource is 'logical_filter'."
    )

def get_router_chain():
    """Creates an LLM chain that routes a query to the appropriate tool."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_llm = llm.with_structured_output(RouteQuery)
    # This prompt is now much more direct and less likely to produce extra text.
    system_prompt = """
    You are an expert routing system. Your task is to route a user's question to the single best data source.
    You must respond with ONLY one of the following options: 'vectorstore', 'graph', or 'logical_filter'.

    - 'vectorstore': For semantic searches, definitions, or general information.
    - 'graph': For questions about relationships, connections, or multi-hop reasoning.
    - 'logical_filter': For precise lookups based on a specific property or attribute.
    
    If you choose 'logical_filter', you MUST also provide the node type, property, and value for the filter.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])
    return prompt | structured_llm