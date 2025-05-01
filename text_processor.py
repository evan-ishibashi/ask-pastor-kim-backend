import json
import faiss
import openai
import tiktoken
import hashlib
import numpy as np
from pathlib import Path
from typing import List

# Config
CHUNK_SIZE = 500
EMBEDDING_MODEL = "text-embedding-3-small"
INPUT_FILE = "lighthouse_pages.json"
EMBEDDED_METADATA_FILE = "embedded_chunks.json"
FAISS_INDEX_FILE = "faiss_index.index"
DRY_RUN = True  # Toggle for safe testing

openai.api_key = "your-api-key-here"

def hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def chunk_text(text: str, chunk_size: int) -> List[str]:
    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    tokens = encoder.encode(text)
    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i + chunk_size]
        decoded = encoder.decode(chunk)
        chunks.append(decoded)
    return chunks

def get_embedding(text: str) -> List[float]:
    response = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def load_existing_chunks():
    if not Path(EMBEDDED_METADATA_FILE).exists():
        return []
    with open(EMBEDDED_METADATA_FILE) as f:
        return json.load(f)

def save_embedded_chunks(chunks):
    with open(EMBEDDED_METADATA_FILE, "w") as f:
        json.dump(chunks, f, indent=2)

def load_or_create_faiss(dim):
    if Path(FAISS_INDEX_FILE).exists():
        return faiss.read_index(FAISS_INDEX_FILE)
    return faiss.IndexFlatL2(dim)

def save_faiss_index(index):
    faiss.write_index(index, FAISS_INDEX_FILE)

def main():
    with open(INPUT_FILE) as f:
        pages = json.load(f)

    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    existing_chunks = load_existing_chunks()
    existing_hashes = set(chunk["hash"] for chunk in existing_chunks)

    new_chunks = []
    total_tokens = 0

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

    print(f"\n🔍 New chunks to embed: {len(new_chunks)}")
    print(f"🔢 Total new tokens: {total_tokens:,}")
    print(f"💰 Estimated cost: ${total_tokens * 0.00002:.4f}")

    if DRY_RUN:
        print("\n🚧 Dry run enabled. No API calls will be made.")
        return

    confirm = input("\n⚠️ Proceed with embedding these new chunks? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Aborted.")
        return

    embeddings = []
    metadata_to_add = []

    print("\n🚀 Starting embedding...")

    for chunk in new_chunks:
        try:
            vector = get_embedding(chunk["text"])
            embeddings.append(vector)
            metadata_to_add.append({
                "hash": chunk["hash"],
                "url": chunk["url"],
                "content": chunk["text"],
                "embedding": vector  # optional: remove if storing separately
            })
        except Exception as e:
            print(f"⚠️ Error embedding chunk from {chunk['url']}: {e}")

    if embeddings:
        dim = len(embeddings[0])
        index = load_or_create_faiss(dim)
        index.add(np.array(embeddings).astype("float32"))
        save_faiss_index(index)
        existing_chunks.extend(metadata_to_add)
        save_embedded_chunks(existing_chunks)
        print(f"\n✅ Embedded {len(embeddings)} new chunks and saved metadata.")
    else:
        print("\n⚠️ No new embeddings added.")

if __name__ == "__main__":
    main()