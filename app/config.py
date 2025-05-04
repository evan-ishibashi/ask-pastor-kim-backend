import os
from dotenv import load_dotenv

load_dotenv()

# Config
CHUNK_SIZE = 500
EMBEDDING_MODEL = "text-embedding-3-small"
LIGHTHOUSE_PAGES = "lighthouse_pages.json"
EMBEDDED_METADATA_FILE = "embedded_chunks.json"
CHUNKS_FILE = "embedded_chunks.json"
CHUNKS_FILE_ID = os.environ.get("EMBEDDED_CHUNKS_FILE_ID")

#API Keys
OPENAI_KEY = os.environ.get("OPENAI_KEY")
PINECONE_KEY = os.environ.get("PINECONE_KEY")

#Pinecone
PINECONE_ENV = os.environ.get("PINECONE_ENV")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX")

# Drive IDs
LIGHTHOUSE_FILE_ID = os.environ.get("LIGHTHOUSE_FILE_ID")
EMBEDDED_CHUNKS_FILE_ID = os.environ.get("EMBEDDED_CHUNKS_FILE_ID")

BATCH_SIZE = 500