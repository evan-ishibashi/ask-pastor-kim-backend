import faiss
import openai
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv
from typing import List

# Load environment variables (API keys, etc.)
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_KEY")

# Load the FAISS index and embedded chunks (we assume these exist already)
FAISS_INDEX_FILE = "faiss_index.index"
EMBEDDED_METADATA_FILE = "embedded_chunks.json"

# Helper functions
def load_existing_chunks():
    """Load existing embedded chunks."""
    if not os.path.exists(EMBEDDED_METADATA_FILE):
        return []
    with open(EMBEDDED_METADATA_FILE) as f:
        return json.load(f)

def load_or_create_faiss(dim):
    """Load or create a FAISS index."""
    if os.path.exists(FAISS_INDEX_FILE):
        return faiss.read_index(FAISS_INDEX_FILE)
    return faiss.IndexFlatL2(dim)

def get_embedding(text: str) -> List[float]:
    """Call OpenAI's API to generate embeddings."""
    response = openai.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def search_faiss(query_embedding, k=5):
    """Search the FAISS index for the top k most relevant chunks."""
    index = load_or_create_faiss(len(query_embedding))
    D, I = index.search(np.array([query_embedding]).astype("float32"), k)
    return I

def generate_answer(context: List[str], question: str) -> str:
    """Use OpenAI to generate an answer based on context and question."""
    prompt = f"Question: {question}\n\nContext: {context}\n\nAnswer:"
    response = openai.Completion.create(
        model="text-davinci-003",  # You can use GPT-3.5 or another model if you prefer
        prompt=prompt,
        max_tokens=150,
    )
    return response.choices[0].text.strip()

# Pydantic model for request data
class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(query_request: QueryRequest):
    """Handle user query, search FAISS index, and return a generated answer."""
    question = query_request.question

    # Step 1: Generate embedding for the query
    query_embedding = get_embedding(question)

    # Step 2: Search FAISS index to get relevant chunks
    indices = search_faiss(query_embedding)
    chunks = load_existing_chunks()

    context = [chunks[i]["content"] for i in indices[0]]  # Get the text of the most relevant chunks

    # Step 3: Generate an answer using the relevant context
    try:
        answer = generate_answer(context, question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

    return {"answer": answer, "sources": context}