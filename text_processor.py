import json
import faiss
import openai
import tiktoken
import hashlib
import numpy as np
import os
import time
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Config
CHUNK_SIZE = 500
EMBEDDING_MODEL = "text-embedding-3-small"
INPUT_FILE = "lighthouse_pages.json"
EMBEDDED_METADATA_FILE = "embedded_chunks.json"
FAISS_INDEX_FILE = "faiss_index.index"
DRY_RUN = False  # Toggle for safe testing

openai.api_key = os.environ.get("OPENAI_KEY")


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

def load_or_create_faiss(dim):
    """Load or create a FAISS index."""
    if Path(FAISS_INDEX_FILE).exists():
        return faiss.read_index(FAISS_INDEX_FILE)
    return faiss.IndexFlatL2(dim)

def save_faiss_index(index):
    """Save the FAISS index to a file."""
    faiss.write_index(index, FAISS_INDEX_FILE)

# Main function to embed new chunks and store embeddings
def main():
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
    confirm = input("\n⚠️ Proceed with embedding these new chunks? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Aborted.")
        return

    # Start embedding in batches
    all_metadata = []
    for batch in get_batches(new_chunks):
        texts = [chunk["text"] for chunk in batch]
        try:
            # Call OpenAI API to get embeddings for the batch
            response = openai.embeddings.create(
                input=texts,
                model=EMBEDDING_MODEL
            )
            vectors = [e.embedding for e in response.data]

            # Prepare metadata and add to the list
            for chunk, vector in zip(batch, vectors):
                metadata = {
                    "hash": chunk["hash"],
                    "url": chunk["url"],
                    "content": chunk["text"],
                    "embedding": vector  # optional: remove if storing separately
                }
                all_metadata.append(metadata)

            # Sleep to avoid rate-limiting
            time.sleep(1)  # Polite delay between batches
        except Exception as e:
            print(f"Error embedding batch: {e}")
            time.sleep(5)  # Optional backoff after error

    # If embeddings were successful, add them to FAISS and save
    if all_metadata:
        # Ensure FAISS index is loaded/created
        dim = len(all_metadata[0]["embedding"])
        index = load_or_create_faiss(dim)
        embeddings = [m["embedding"] for m in all_metadata]
        index.add(np.array(embeddings).astype("float32"))

        # Save the new FAISS index
        save_faiss_index(index)

        # Save the new metadata
        existing_chunks.extend(all_metadata)
        save_embedded_chunks(existing_chunks)

        print(f"\n✅ Embedded {len(embeddings)} new chunks and saved metadata.")
    else:
        print("\n⚠️ No new embeddings added.")

if __name__ == "__main__":
    main()