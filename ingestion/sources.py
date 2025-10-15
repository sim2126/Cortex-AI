# /ingestion/sources.py

from abc import ABC, abstractmethod
from typing import List
import os
import requests
from bs4 import BeautifulSoup

from langchain.docstore.document import Document
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader

class DataSource(ABC):
    """Abstract base class for a data source."""
    @abstractmethod
    def load_documents(self) -> List[Document]:
        """Loads documents from the source and returns them as a list."""
        pass

class LocalDirectorySource(DataSource):
    """Loads all PDF documents from a specified local directory."""
    def __init__(self, path: str):
        if not os.path.isdir(path):
            raise ValueError(f"The path {path} is not a valid directory.")
        self.path = path

    def load_documents(self) -> List[Document]:
        print(f"--- Loading documents from Local Directory: {self.path} ---")
        all_docs = []
        for filename in os.listdir(self.path):
            if filename.endswith(".pdf"):
                file_path = os.path.join(self.path, filename)
                try:
                    loader = PyPDFLoader(file_path)
                    all_docs.extend(loader.load())
                    print(f"  - Successfully loaded {filename}")
                except Exception as e:
                    print(f"  - FAILED to load {filename}: {e}")
        return all_docs

class WebUrlSource(DataSource):
    """Loads documents from a list of web URLs."""
    def __init__(self, urls: List[str]):
        self.urls = urls

    def load_documents(self) -> List[Document]:
        print("--- Loading documents from Web URLs ---")
        loader = WebBaseLoader(self.urls)
        loader.requests_per_second = 1 # Be respectful to servers
        try:
            docs = loader.load()
            print(f"  - Successfully loaded {len(self.urls)} URL(s).")
            return docs
        except Exception as e:
            print(f"  - FAILED to load URLs: {e}")
            return []