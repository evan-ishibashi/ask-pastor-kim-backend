from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pinecone import Pinecone
from openai import OpenAI
import numpy as np
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.config import OPENAI_KEY, PINECONE_KEY, PINECONE_INDEX


# Initialize FastAPI
app = FastAPI()

# Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify allowed origins, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAI API Key
client = OpenAI(api_key=OPENAI_KEY)

# Load PineCone API Key
pc = Pinecone(PINECONE_KEY)
index = pc.Index(PINECONE_INDEX)


# Request schema
class QuestionRequest(BaseModel):
    question: str

# Route
@app.post("/ask")
async def ask_question(req: QuestionRequest):
    try:
        # Step 1: Embed the question
        embedding_response = client.embeddings.create(
            input=req.question,
            model="text-embedding-3-small"
        )
        query_vector = embedding_response.data[0].embedding

        # Normalize the query vector
        normal_query_vector = np.array(query_vector) / np.linalg.norm(query_vector)
        query_vector_list = normal_query_vector.tolist()
        print(query_vector_list)

        # Log the query vector
        logging.info(f"Query Vector: {normal_query_vector}")

        # Step 2: Query Pinecone
        pinecone_response = index.query(
            vector=query_vector_list,
            top_k=5,
            namespace="ns1",
            include_metadata=True
        )

        logging.info(f"Pinecone Response: {pinecone_response}")

        print (pinecone_response.matches)

        if not pinecone_response.matches:
            return {"answer": "No relevant documents found.", "sources": []}

        # Step 3: Build context
        context = [match.metadata["text"] for match in pinecone_response.matches]
        sources = [
            {
                "url": match.metadata.get("url", "No URL provided"),
                "content": match.metadata.get("text", "")
            }
            for match in pinecone_response.matches
            if match.score > 0.5
        ]

        # Step 4: Send prompt to OpenAI Chat API
        prompt = (
            f"Answer the question based on the following context:\n\n"
            + "\n---\n".join(context)
            + f"\n\nQuestion: {req.question}"
        )

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are an assistant solely for helping people learn more about all things lighthouse community church."
                    )},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )

        answer = completion.choices[0].message.content.strip()

        return {"answer": answer, "sources": sources}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))