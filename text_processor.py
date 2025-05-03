import json
import openai
import tiktoken
import hashlib
import os
import time
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from gdrive_helpers import authenticate_drive, download_file_from_drive, upload_file_to_drive


load_dotenv()

# Config
CHUNK_SIZE = 500
EMBEDDING_MODEL = "text-embedding-3-small"
INPUT_FILE = "lighthouse_pages.json"
EMBEDDED_METADATA_FILE = "embedded_chunks.json"
DRY_RUN = False  # Toggle for safe testing

#API Keys
openai.api_key = os.environ.get("OPENAI_KEY")
pinecone_env = os.environ.get("PINECONE_ENV")
pinecone_index_name = os.environ.get("PINECONE_INDEX")

# Initialize Pinecone
pc = Pinecone(os.environ.get("PINECONE_KEY"))
index = pc.Index(pinecone_index_name)
if pinecone_index_name not in pc.list_indexes().names():
    pc.create_index(
        name=pinecone_index_name,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )



# Helper functions
def hash_text(text: str) -> str:
    """Generate a hash for deduplication."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def chunk_text(text: str, chunk_size: int) -> List[str]:
    """Split text into chunks of fixed size."""
    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    tokens = encoder.encode(text)
    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i + chunk_size]
        decoded = encoder.decode(chunk)
        chunks.append(decoded)
    return chunks

def count_tokens(text: str) -> int:
    """Count the number of tokens in a text."""
    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    return len(encoder.encode(text))

def get_batches(chunks, max_tokens=2048):
    """Group chunks into batches under the token limit."""
    batch, batch_tokens = [], 0
    for chunk in chunks:
        tokens = count_tokens(chunk["text"])
        if batch_tokens + tokens > max_tokens:
            yield batch
            batch, batch_tokens = [], 0
        batch.append(chunk)
        batch_tokens += tokens
    if batch:
        yield batch

def get_embedding(text: str) -> List[float]:
    """Call OpenAI's API to generate embeddings."""
    response = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def load_existing_chunks():
    """Load existing embedded chunks."""
    if not Path(EMBEDDED_METADATA_FILE).exists():
        return []
    with open(EMBEDDED_METADATA_FILE) as f:
        return json.load(f)

def save_embedded_chunks(chunks):
    """Save the embedded chunk metadata."""
    with open(EMBEDDED_METADATA_FILE, "w") as f:
        json.dump(chunks, f, indent=2)

# Main function to embed new chunks and store embeddings
def main():
    drive = authenticate_drive()

    # File IDs retrieved from .env
    LIGHTHOUSE_FILE_ID = os.environ.get("LIGHTHOUSE_FILE_ID")
    EMBEDDED_CHUNKS_FILE_ID = os.environ.get("EMBEDDED_CHUNKS_FILE_ID")

    # Download latest versions before processing
    download_file_from_drive(drive, LIGHTHOUSE_FILE_ID, "lighthouse_pages.json")
    download_file_from_drive(drive, EMBEDDED_CHUNKS_FILE_ID, "embedded_chunks.json")

    with open(INPUT_FILE) as f:
        pages = json.load(f)

    # Load existing chunks and hashes for deduplication
    existing_chunks = load_existing_chunks()
    existing_hashes = set(chunk["hash"] for chunk in existing_chunks)

    # Tokenizer and batch setup
    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    new_chunks = []
    total_tokens = 0

    # Process each page's text
    for page in pages:
        url = page["url"]
        text = page["text"]
        chunks = chunk_text(text, CHUNK_SIZE)

        for chunk in chunks:
            h = hash_text(chunk)
            if h in existing_hashes:
                continue
            token_count = len(encoder.encode(chunk))
            total_tokens += token_count
            new_chunks.append({
                "hash": h,
                "url": url,
                "text": chunk,
                "tokens": token_count
            })

    # Show information about the new chunks and estimated cost
    print(f"\n🔍 New chunks to embed: {len(new_chunks)}")
    print(f"🔢 Total new tokens: {total_tokens:,}")
    print(f"💰 Estimated cost: ${total_tokens * 0.00002:.4f}")

    if DRY_RUN:
        print("\n🚧 Dry run enabled. No API calls will be made.")
        return

    # Confirm before proceeding
    confirm = input("\n⚠️ Proceed with embedding these chunks to Pinecone? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Aborted.")
        return

    all_metadata = []

    for batch in get_batches(new_chunks):
        texts = [chunk["text"] for chunk in batch]
        try:
            response = openai.embeddings.create(input=texts, model=EMBEDDING_MODEL)
            vectors = [e.embedding for e in response.data]

            pinecone_data = []
            for chunk, vector in zip(batch, vectors):
                pinecone_data.append((
                    chunk["hash"],  # unique ID
                    vector,
                    {"url": chunk["url"], "text": chunk["text"]}
                ))
                all_metadata.append({
                    "hash": chunk["hash"],
                    "url": chunk["url"],
                    "text": chunk["text"],
                    "tokens": chunk["tokens"]
                })

            index.upsert(vectors=pinecone_data,namespace="ns1")

            time.sleep(1)  # Be polite to OpenAI API
        except Exception as e:
            print(f"⚠️ Error embedding batch: {e}")
            time.sleep(5)

    if all_metadata:
        existing_chunks.extend(all_metadata)
        save_embedded_chunks(existing_chunks)
        upload_file_to_drive(drive, EMBEDDED_METADATA_FILE, EMBEDDED_CHUNKS_FILE_ID)
        print(f"\n✅ Successfully embedded {len(all_metadata)} new chunks to Pinecone.")
    else:
        print("\n⚠️ No new embeddings added.")

if __name__ == "__main__":
    main()