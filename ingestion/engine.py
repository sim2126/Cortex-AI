import os
from dotenv import load_dotenv
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS

from core.config import settings
from core.models import KnowledgeGraph
from ingestion.sources import DataSource

# Note: We are removing graph extraction from the ingestion engine to focus on pure RAG.
# from core.graph_builder import get_latest_ontology, extract_and_embed_graph
# from core.database import Neo4jDatabase
# from core.entity_resolver import EntityResolver

class IngestionEngine:
    def __init__(self, data_sources: List[DataSource]):
        self.data_sources = data_sources
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        self.embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)

    def run(self):
        """
        Runs the ingestion pipeline:
        1. Loads data from all sources.
        2. Chunks documents and creates/updates a vector store.
        """
        all_documents = []
        for source in self.data_sources:
            all_documents.extend(source.load_documents())
        
        if not all_documents:
            print("No documents loaded. Exiting ingestion.")
            return

        chunks = self.text_splitter.split_documents(all_documents)
        print(f"\nTotal documents split into {len(chunks)} chunks.")
        self._create_or_update_vector_store(chunks)

        print("\n--- Ingestion process complete. ---")


    def _create_or_update_vector_store(self, chunks):
        """
        Creates a FAISS vector store or adds to an existing one.
        This version is more robust and checks for the index file itself.
        """
        vector_store_path = settings.VECTOR_STORE_PATH
        index_file_path = os.path.join(vector_store_path, "index.faiss")

        # --- THIS IS THE CORRECTED LOGIC ---
        # We now check for the actual index file, not just the directory.
        if os.path.exists(index_file_path):
            print("Existing vector store found. Adding new documents...")
            local_store = FAISS.load_local(
                vector_store_path, 
                self.embeddings_model, 
                allow_dangerous_deserialization=True
            )
            local_store.add_documents(chunks)
        else:
            print("Creating new FAISS vector store...")
            os.makedirs(vector_store_path, exist_ok=True)
            local_store = FAISS.from_documents(chunks, self.embeddings_model)
        
        local_store.save_local(vector_store_path)
        print(f"Vector store saved at: {vector_store_path}")
