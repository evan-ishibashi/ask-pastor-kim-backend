import json
from pinecone import Pinecone, ServerlessSpec
from gdrive_helpers import authenticate_drive, download_file_from_drive
import os
from dotenv import load_dotenv
from pinecone_helpers import batch_upload

load_dotenv()


# === CONFIG ===
PINECONE_API_KEY = os.environ.get("PINECONE_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX")
CHUNKS_FILE = "embedded_chunks.json"
CHUNKS_FILE_ID = os.environ.get("EMBEDDED_CHUNKS_FILE_ID") # 🔑 Get this from Drive URL
BATCH_SIZE = 500


def load_chunks(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    print("🔐 Authenticating Google Drive...")
    service = authenticate_drive()

    print(f"📥 Downloading {CHUNKS_FILE} from Google Drive...")
    download_file_from_drive(service, CHUNKS_FILE_ID, CHUNKS_FILE)

    print("🚀 Initializing Pinecone...")
    pc = Pinecone(PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX_NAME)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )


    print(f"📦 Loading chunks from {CHUNKS_FILE}...")
    chunks = load_chunks(CHUNKS_FILE)
    vectors = [
        (chunk["hash"], chunk["embedding"], {"url": chunk["url"], "text": chunk["text"]})
        for chunk in chunks
    ]

    print(f"📤 Uploading {len(vectors)} vectors to Pinecone...")
    batch_upload(index, vectors, 100)

    print("✅ Upload complete!")


if __name__ == "__main__":
    main()
