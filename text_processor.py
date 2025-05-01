# backend/text_processor.py

import json
import re
import sys
import os

CHUNK_SIZE = 2000  # characters per chunk

def clean_and_chunk_page(text, url):
    # Normalize whitespace and line breaks
    text = re.sub(r"\n\s*\n+", "\n\n", text.strip())

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_SIZE:
            current += para + "\n\n"
        else:
            if current.strip():
                chunks.append({"url": url, "content": current.strip()})
            current = para + "\n\n"

    if current.strip():
        chunks.append({"url": url, "content": current.strip()})

    return chunks

def process_scraped_json(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"❌ Input file {input_file} not found.")
        return

    with open(input_file, "r") as f:
        pages = json.load(f)

    all_chunks = []
    for page in pages:
        url = page.get("url", "unknown")
        text = page.get("text", "")
        if text:
            chunks = clean_and_chunk_page(text, url)
            all_chunks.extend(chunks)

    with open(output_file, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"✅ Processed {len(pages)} pages into {len(all_chunks)} chunks.")
    print(f"📄 Output written to {output_file}")

# ✅ CLI entry point
if __name__ == "__main__":
    # Usage: python text_processor.py [input_file] [output_file]
    input_file = sys.argv[1] if len(sys.argv) > 1 else "lighthouse_pages.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "lighthouse_chunks.json"

    process_scraped_json(input_file, output_file)