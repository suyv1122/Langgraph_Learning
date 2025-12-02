from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
# 基础配置文件
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "data" / "docs"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"    # 向量数据库的项目内绝对路径

class Settings(BaseModel):
    base_dir: Path = BASE_DIR
    docs_dir: Path = DOCS_DIR
    openai_api_key: str = os.getenv("My_learning_test_Key", "")
    # model_name: str = os.getenv("MODEL_NAME", "gemma2:9b")
    model_name: str = os.getenv("MODEL_NAME", "llama3.2")
    chroma_dir: str = CHROMA_DIR
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
    collection_name: str = os.getenv("COLLECTION_NAME", "knowledge_base")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))

settings = Settings()
