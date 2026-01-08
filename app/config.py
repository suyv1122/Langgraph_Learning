from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
# 基础配置文件
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "data" / "docs"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"    # 向量数据库的项目内绝对路径
DATA_MEMORY_DIR = BASE_DIR / "data" / "memory"

class Settings(BaseModel):
    base_dir: Path = BASE_DIR
    docs_dir: Path = DOCS_DIR
    memory_dir: Path = DATA_MEMORY_DIR
    openai_api_key: str = os.getenv("My_learning_test_Key", "")
    model_name: str = os.getenv("MODEL_NAME", "gemma2:9b")
    # model_name: str = os.getenv("MODEL_NAME", "llama3.2")
    chroma_dir: str = CHROMA_DIR
    chroma_host: str = os.getenv("CHROMA_HOST", "127.0.0.1")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
    collection_name: str = os.getenv("COLLECTION_NAME", "knowledge_base")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    audio_collection_name: str = os.getenv("AUDIO_COLLECTION_NAME", "audio_base")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", 'amqp://Ame:123456@127.0.0.1:5672/%2F')
    # docker run -d --name rmq \
    #   -p 5672:5672 \
    #   -p 15672:15672 \
    #   -e RABBITMQ_DEFAULT_USER=Ame \
    #   -e RABBITMQ_DEFAULT_PASS=123456 \
    #   rabbitmq:4.2-management
    celery_audio_queue: str ='audio' # 消息队列的名字

    audio_dir: str = BASE_DIR / "data" / "audio"
    audio_wav_dir: str = BASE_DIR / "data" / "audio_wav"
    audio_clip_dir: str = BASE_DIR / "data" / "audio_clips"

settings = Settings()