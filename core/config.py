from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Centralized application settings. Pydantic's BaseSettings will automatically
    load these from environment variables or a .env file.
    """
    # --- LLM and Embedding Models ---
    GENERATION_MODEL: str = Field("gemini-2.5-flash", description="The primary model for generation and reasoning.")
    EMBEDDING_MODEL: str = Field("models/embedding-001", description="The model used for creating text embeddings.")
    FAST_MODEL: str = Field("gemini-2.5-flash", description="The model for fast tasks like routing and classification.")
    
    # --- Neo4j Database Credentials ---
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    
    # --- AWS Neptune Credentials (New) ---
    NEPTUNE_ENDPOINT: str = Field("", description="The WebSocket endpoint for the Neptune cluster.")
    NEPTUNE_USERNAME: str = Field("", description="Username for Neptune DB.")
    NEPTUNE_PASSWORD: str = Field("", description="Password for Neptune DB.")
    
    # --- Google API Key ---
    GOOGLE_API_KEY: str

    # --- System Parameters ---
    VECTOR_STORE_PATH: str = Field("vector_store", description="Path to the FAISS vector store.")
    ENTITY_SIMILARITY_THRESHOLD: float = Field(0.90, description="Cosine similarity threshold for merging entities.")
    EMBEDDING_DIMENSIONS: int = Field(768, description="Dimensions of the text embeddings (Gemini is 768).")

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()