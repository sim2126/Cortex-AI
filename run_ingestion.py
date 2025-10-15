# /run_ingestion.py

import os
from dotenv import load_dotenv

from ingestion.engine import IngestionEngine
from ingestion.sources import LocalDirectorySource, WebUrlSource

def main():
    """
    Main function to configure and run the ingestion pipeline.
    """
    load_dotenv()
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in .env file.")
        return

    # --- Configure Your Data Sources Here ---
    
    # Example 1: Ingest all PDFs from the './data' directory
    local_source = LocalDirectorySource(path=os.path.join(os.path.dirname(__file__), 'data'))
    
    # Example 2: Ingest content from a list of web pages
    web_source = WebUrlSource(urls=[
        "https://en.wikipedia.org/wiki/Knowledge_graph",
        "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
    ])
    
    # --- Run the Ingestion Engine ---
    
    # You can combine multiple sources
    engine = IngestionEngine(data_sources=[local_source, web_source])
    engine.run()


if __name__ == '__main__':
    main()