from fastapi import APIRouter, HTTPException
from typing import List
import os
import shutil
from pathlib import Path

# Add the root directory to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import settings

router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"]
)

@router.get("/sources", response_model=List[str])
def get_knowledge_sources():
    """
    Inspects the vector store and returns a list of unique source documents
    that have been ingested into the knowledge base.
    """
    vector_store_path = settings.VECTOR_STORE_PATH
    if not os.path.exists(vector_store_path):
        return []

    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)
        vector_store = FAISS.load_local(
            vector_store_path,
            embeddings_model,
            allow_dangerous_deserialization=True
        )
        
        # Extract unique sources from the document metadata
        sources = set()
        # Check if the docstore and its dictionary exist
        if hasattr(vector_store, 'docstore') and hasattr(vector_store.docstore, '_dict'):
            for doc in vector_store.docstore._dict.values():
                source_name = os.path.basename(doc.metadata.get('source', 'Unknown Source'))
                sources.add(source_name)
            
        return sorted(list(sources))
        
    except Exception as e:
        # Return an empty list if the vector store is corrupt or empty
        print(f"Could not load sources from vector store, it might be empty. Error: {e}")
        return []

@router.delete("/clear")
def clear_knowledge_base():
    """Deletes the entire vector store and graph database, effectively clearing the knowledge base."""
    vector_store_path = settings.VECTOR_STORE_PATH
    
    try:
        # Clear the vector store
        if os.path.exists(vector_store_path):
            shutil.rmtree(vector_store_path)
            # Recreate the directory so it's ready for the next ingestion
            os.makedirs(vector_store_path, exist_ok=True)
        
        # Placeholder for clearing the graph database
        # In a real application, you would connect to Neo4j/Neptune and run a delete query.
        # For example: from core.database import Neo4jDatabase
        # db = Neo4jDatabase()
        # db.execute_query("MATCH (n) DETACH DELETE n")
        # db.close()

        return {"message": "Knowledge base (vector store) cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear knowledge base: {e}")

