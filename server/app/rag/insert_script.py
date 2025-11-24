#!/usr/bin/env python3
"""
Script to process PDF files from rag/context directory and store them in Pinecone vector database.

Usage:
    cd server
    python app/rag/insert_script.py
"""
import os
import sys
import time
import re
import textwrap
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

# Load environment variables from server/.env file
# Try to find .env file in server directory (3 levels up from this script)
server_dir = Path(__file__).parent.parent.parent
env_file = server_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Fallback to default .env search
    load_dotenv()

# Configuration
INDEX_NAME = "carely"
NAMESPACE = "carely"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMENSION = 1536
DEFAULT_CHUNK_SIZE = 9
DEFAULT_STRIDE = 3

# Get script directory and context directory
SCRIPT_DIR = Path(__file__).parent
CONTEXT_DIR = SCRIPT_DIR / "context"


def extract_clean_120_list(pdf_path: str) -> List[str]:
    """
    Extract and clean PDF text, return as list of lines wrapped at 120 characters.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of cleaned text lines, each wrapped at 120 characters
    """
    doc = fitz.open(pdf_path)
    raw = "\n".join(page.get_text() for page in doc)
    doc.close()

    # Fix hyphenations and unwrap soft breaks
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', raw)
    text = re.sub(r'(?<![.!?;:])\n(?!\n)', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Split into paragraphs, wrap to 120 chars
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    wrapped_paras = [
        textwrap.fill(p, width=120, break_long_words=False, break_on_hyphens=False)
        for p in paras
    ]

    # Flatten paragraphs into list of lines
    lines = []
    for para in wrapped_paras:
        lines.extend(para.splitlines())
        lines.append("")  # Keep blank line between paragraphs
    
    if lines and lines[-1] == "":
        lines.pop()  # Remove trailing blank line

    return lines


def nlp_upsert(
    filename: str,
    index_name: str,
    namespace: str,
    nlp_id: str,
    chunk_size: int,
    stride: int,
    client: OpenAI,
    pc: Pinecone,
    embed_model: str
) -> int:
    """
    Process a PDF file and upsert chunks to Pinecone vector database.

    Args:
        filename: Path to the PDF file
        index_name: Pinecone index name
        namespace: Pinecone namespace
        nlp_id: Common ID prefix for document chunks
        chunk_size: Number of lines per chunk
        stride: Number of lines overlap between chunks
        client: OpenAI client
        pc: Pinecone client
        embed_model: Embedding model name
        
    Returns:
        Number of chunks upserted
    """
    print(f"\n{'='*80}")
    print(f"Processing: {filename}")
    print(f"{'='*80}")
    
    print("Extracting PDF...")
    doc = extract_clean_120_list(filename)
    print(f"Extraction finished! Total Lines: {len(doc)}")
    
    # Connect to index
    index = pc.Index(index_name)
    
    count = 0
    for i in range(0, len(doc), chunk_size):
        # Find beginning and end of the chunk (with overlap)
        i_begin = max(0, i - stride)
        i_end = min(len(doc), i_begin + chunk_size)
        
        doc_chunk = doc[i_begin:i_end]
        print(f"\n{'-'*80}")
        print(f"Chunk {i//chunk_size + 1} (lines {i_begin}-{i_end}):")
        print(f"{'-'*80}")
        
        # Combine chunk lines into text
        texts = "".join(doc_chunk)
        print(f"Text preview: {texts[:200]}..." if len(texts) > 200 else f"Text: {texts}")
        
        # Create embeddings of the chunk texts
        try:
            res = client.embeddings.create(input=texts, model=embed_model)
        except Exception as e:
            print(f"Error creating embedding: {e}")
            print("Retrying in 10 seconds...")
            done = False
            while not done:
                time.sleep(10)
                try:
                    res = client.embeddings.create(input=texts, model=embed_model)
                    done = True
                except Exception as retry_error:
                    print(f"Retry failed: {retry_error}")
                    print("Waiting 10 more seconds...")
        
        embed = res.data[0].embedding
        print(f"Embedding length: {len(embed)}")

        # Metadata preparation
        metadata = {
            "text": texts,
            "source_file": os.path.basename(filename),
            "chunk_index": count + 1
        }

        count += 1
        vector_id = f"{nlp_id}_{count}"
        print(f"Upserting vector: {vector_id}")
        print(f"{'='*80}")

        # Upsert to Pinecone
        index.upsert(
            vectors=[{
                "id": vector_id,
                "metadata": metadata,
                "values": embed
            }],
            namespace=namespace
        )
    
    print(f"\n✅ Successfully upserted {count} chunks from {os.path.basename(filename)}")
    return count


def check_or_create_index(pc: Pinecone, index_name: str, dimension: int) -> None:
    """
    Check if Pinecone index exists, create if it doesn't.
    
    Args:
        pc: Pinecone client
        index_name: Name of the index
        dimension: Vector dimension
    """
    # Get list of existing indexes
    try:
        existing_indexes = pc.list_indexes()
        # Handle different Pinecone client versions
        if hasattr(existing_indexes, 'names'):
            index_names = existing_indexes.names()
        elif hasattr(existing_indexes, '__iter__'):
            index_names = [idx.name for idx in existing_indexes]
        else:
            index_names = []
    except Exception as e:
        print(f"⚠️  Warning: Could not list indexes: {e}")
        index_names = []
    
    if index_name not in index_names:
        print(f"Index '{index_name}' not found. Creating...")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            deletion_protection="disabled",
            tags={"environment": "development"},
            vector_type="dense",
        )
        print("Waiting for index to be ready...")
        # Wait until ready
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
        print("✅ Index ready!")
    else:
        print(f"✅ Index '{index_name}' already exists")


def main():
    """Main function to process PDFs and insert into Pinecone"""
    # Check for required environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    
    if not openai_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        sys.exit(1)
    
    if not pinecone_key:
        print("❌ Error: PINECONE_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        sys.exit(1)
    
    # Initialize clients
    print("🔧 Initializing clients...")
    client = OpenAI(api_key=openai_key)
    pc = Pinecone(api_key=pinecone_key)
    print("✅ Clients initialized")
    
    # Check or create index
    print(f"\n📊 Checking Pinecone index '{INDEX_NAME}'...")
    check_or_create_index(pc, INDEX_NAME, EMBED_DIMENSION)
    
    # Scan for PDF files
    if not CONTEXT_DIR.exists():
        print(f"❌ Error: Context directory not found: {CONTEXT_DIR}")
        sys.exit(1)
    
    pdf_files = list(CONTEXT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {CONTEXT_DIR}")
        sys.exit(1)
    
    print(f"\n📄 Found {len(pdf_files)} PDF file(s) to process:")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file.name}")
    
    # Process each PDF
    total_chunks = 0
    for pdf_file in pdf_files:
        # Extract filename without extension for nlp_id
        nlp_id = pdf_file.stem.lower().replace(" ", "_").replace("-", "_")
        
        try:
            chunks = nlp_upsert(
                filename=str(pdf_file),
                index_name=INDEX_NAME,
                namespace=NAMESPACE,
                nlp_id=nlp_id,
                chunk_size=DEFAULT_CHUNK_SIZE,
                stride=DEFAULT_STRIDE,
                client=client,
                pc=pc,
                embed_model=EMBED_MODEL
            )
            total_chunks += chunks
        except Exception as e:
            print(f"❌ Error processing {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Print summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}")
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total chunks upserted: {total_chunks}")
    print(f"Index: {INDEX_NAME}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Embedding model: {EMBED_MODEL}")
    
    # Show index stats
    try:
        index = pc.Index(INDEX_NAME)
        stats = index.describe_index_stats()
        print(f"\n📈 Index Statistics:")
        print(f"   Total vectors: {stats.get('total_vector_count', 'N/A')}")
        if 'namespaces' in stats:
            for ns_name, ns_stats in stats['namespaces'].items():
                print(f"   Namespace '{ns_name}': {ns_stats.get('vector_count', 'N/A')} vectors")
    except Exception as e:
        print(f"⚠️  Could not retrieve index stats: {e}")
    
    print(f"\n✅ Done!")


if __name__ == "__main__":
    main()
