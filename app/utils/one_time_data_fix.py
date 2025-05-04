import json
from app.utils.gdrive_helpers import authenticate_drive, download_file_from_drive, upload_file_to_drive
import os
from dotenv import load_dotenv

load_dotenv()


# === CONFIG ===
PINECONE_API_KEY = os.environ.get("PINECONE_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX")
CHUNKS_FILE = "embedded_chunks.json"
CHUNKS_FILE_ID = os.environ.get("EMBEDDED_CHUNKS_FILE_ID") # 🔑 Get this from Drive URL


def load_chunks(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    print("🔐 Authenticating Google Drive...")
    service = authenticate_drive()

    print(f"📥 Downloading {CHUNKS_FILE} from Google Drive...")
    download_file_from_drive(service, CHUNKS_FILE_ID, CHUNKS_FILE)


    print(f"📦 Loading chunks from {CHUNKS_FILE}...")
    data = load_chunks(CHUNKS_FILE)

    for chunk in data:
        if "content" in chunk:
            chunk["text"] = chunk.pop("content")

    with open("embedded_chunks.json", "w") as f:
        json.dump(data, f, indent=2)

    print("✅ Updated 'content' to 'text' in embedded_chunks.json")

    upload_file_to_drive(service, CHUNKS_FILE, CHUNKS_FILE_ID)

    print("✅ uploaded data back to drive")


if __name__ == "__main__":
    main()