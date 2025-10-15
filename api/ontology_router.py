from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import datetime
import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.models import Ontology

# --- Pydantic Models ---
class OntologyVersion(BaseModel):
    version: int
    createdAt: str
    ontology: Ontology

class SuggestionResponse(BaseModel):
    suggestions: List[str] = Field(description="A list of suggested additions or changes to the ontology.")

# --- Router Initialization ---
router = APIRouter(
    prefix="/ontology",
    tags=["Ontology Management"]
)

ONTOLOGY_FILE = "ontology_store.json"

# --- Helper Function to Initialize Store ---
def _initialize_store_if_missing():
    """Creates a default ontology_store.json if it doesn't exist."""
    if not os.path.exists(ONTOLOGY_FILE):
        default_store = {
            "versions": [
                {
                    "version": 1,
                    "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "ontology": {
                        "node_types": ["Person", "Organization", "Technology", "Location", "Concept"],
                        "edge_labels": ["CEO_OF", "WORKS_AT", "ACQUIRED", "LOCATED_IN", "FOUNDED", "USES"]
                    }
                }
            ],
            "latest_version": 1
        }
        with open(ONTOLOGY_FILE, 'w') as f:
            json.dump(default_store, f, indent=2)
        logging.info(f"Created default {ONTOLOGY_FILE}")

# --- Helper Function ---
def _get_latest_ontology_version_from_store() -> OntologyVersion:
    """Helper to load the store and return the latest ontology as a Pydantic model."""
    # Ensure the store exists
    _initialize_store_if_missing()
    
    try:
        with open(ONTOLOGY_FILE, 'r') as f:
            store = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading ontology store: {e}")
        raise HTTPException(status_code=500, detail=f"Could not load or parse ontology_store.json: {e}")

    latest_version_number = store.get('latest_version')
    if not latest_version_number:
        raise HTTPException(status_code=500, detail="'latest_version' key missing in ontology_store.json")

    versions = store.get('versions', [])
    latest_ontology_data = next((v for v in versions if v.get('version') == latest_version_number), None)

    if not latest_ontology_data:
        raise HTTPException(status_code=404, detail=f"Ontology version {latest_version_number} not found.")

    return OntologyVersion(**latest_ontology_data)


# --- API Endpoints ---

@router.get("/", response_model=OntologyVersion)
def get_latest_ontology():
    """Retrieves the latest version of the ontology."""
    return _get_latest_ontology_version_from_store()


@router.post("/", response_model=OntologyVersion)
def update_ontology(new_ontology: Ontology):
    """Creates a new version of the ontology."""
    # Ensure the store exists
    _initialize_store_if_missing()
    
    try:
        with open(ONTOLOGY_FILE, 'r') as f:
            store = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        store = {"versions": [], "latest_version": 0}

    new_version_number = store.get('latest_version', 0) + 1
    
    new_version_data = {
        "version": new_version_number,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ontology": new_ontology.dict()
    }
    
    store['versions'].append(new_version_data)
    store['latest_version'] = new_version_number
    
    with open(ONTOLOGY_FILE, 'w') as f:
        json.dump(store, f, indent=2)
    
    return OntologyVersion(**new_version_data)


@router.post("/suggest", response_model=SuggestionResponse)
async def get_ontology_suggestions(context: str = Body(..., embed=True)):
    """Provides LLM-powered suggestions for improving the ontology."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    prompt = ChatPromptTemplate.from_template(
        """
        You are a knowledge architect. Based on the current ontology and the new text context,
        suggest a list of new node types or edge labels that would improve the graph's expressiveness.
        
        Current Ontology:
        {current_ontology}

        New Text Context:
        ---
        {context}
        ---

        Return a JSON object with a single key "suggestions" containing a list of strings.
        """
    )
    
    latest_ontology_version = _get_latest_ontology_version_from_store()
    
    chain = prompt | llm | JsonOutputParser()
    
    result = await chain.ainvoke({
        "current_ontology": latest_ontology_version.ontology.dict(),
        "context": context
    })
    
    return result