import tqdm

# Upload in batches to avoid 4MB limit
def batch_upload(index, vectors, batch_size=100, namespace="ns1"):
    for i in tqdm(range(0, len(vectors), batch_size), desc="Uploading"):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)