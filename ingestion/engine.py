# /ingestion/engine.py

import os
from dotenv import load_dotenv
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI # Add ChatGoogleGenerativeAI here
from langchain_community.vectorstores import FAISS

from core.config import settings
# We need to import the new models file to use KnowledgeGraph
from core.models import KnowledgeGraph 
from core.graph_builder import get_latest_ontology, extract_and_embed_graph
from core.database import Neo4jDatabase
from core.entity_resolver import EntityResolver
from ingestion.sources import DataSource

class IngestionEngine:
    def __init__(self, data_sources: List[DataSource]):
        self.data_sources = data_sources
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        self.embeddings_model = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.db_client = Neo4jDatabase()

    def run(self):
        """
        Runs the full ingestion pipeline:
        1. Loads data from all sources.
        2. Chunks documents and creates a vector store.
        3. Extracts, resolves, and writes a knowledge graph for each document.
        """
        # 1. Load documents from all sources
        all_documents = []
        for source in self.data_sources:
            all_documents.extend(source.load_documents())
        
        if not all_documents:
            print("No documents loaded. Exiting ingestion.")
            return

        # 2. Split documents and create/update the vector store
        chunks = self.text_splitter.split_documents(all_documents)
        print(f"\nTotal documents split into {len(chunks)} chunks.")
        self._create_or_update_vector_store(chunks)

        # 3. Process each document for knowledge graph extraction
        ontology = get_latest_ontology()
        resolver = EntityResolver(self.db_client, self.embeddings_model)
        
        for doc in all_documents:
            print(f"\n--- Processing document for KG: {doc.metadata.get('source', 'Unknown')} ---")
            raw_graph = extract_and_embed_graph(doc.page_content, self.llm, self.embeddings_model, ontology)
            if raw_graph and raw_graph.nodes:
                resolved_graph = resolver.resolve_and_merge_graph(raw_graph)
                self.db_client.write_graph(resolved_graph)
                print("  - Successfully wrote resolved graph to database.")
            else:
                print("  - No graph data extracted from this document.")

        self.db_client.close()
        print("\n--- Ingestion process complete. ---")


    def _create_or_update_vector_store(self, chunks):
        """Creates a FAISS vector store or adds to an existing one."""
        vector_store_path = settings.VECTOR_STORE_PATH
        if os.path.exists(vector_store_path):
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