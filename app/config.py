from pydantic import BaseModel
from dotenv import load_dotenv
import os
# 基础配置文件
load_dotenv()

class Settings(BaseModel):
    openai_api_key: str = os.getenv("My_learning_test_Key", "")
    model_name: str = os.getenv("MODEL_NAME", "gemma2:9b")
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
    collection_name: str = os.getenv("COLLECTION_NAME", "knowledge_base")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))

settings = Settings()
