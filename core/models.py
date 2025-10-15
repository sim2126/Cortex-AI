# /core/models.py

from typing import List, Optional
from pydantic import BaseModel, Field

# This file will now hold all the shared Pydantic data structures.

class Node(BaseModel):
    id: str = Field(description="A unique identifier for the node, often the entity's name.")
    type: str = Field(description="The type or category of the entity (e.g., Person, Organization, Concept).")
    embedding: Optional[List[float]] = Field(description="The vector embedding of the node.", default=None)

class Edge(BaseModel):
    source: str = Field(description="The ID of the source node.")
    target: str = Field(description="The ID of the target node.")
    label: str = Field(description="The type of relationship between the source and target nodes (e.g., FOUNDED, WORKS_AT, LOCATED_IN).")

class KnowledgeGraph(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

class Ontology(BaseModel):
    node_types: List[str]
    edge_labels: List[str]