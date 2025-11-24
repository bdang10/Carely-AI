"""
RAG Service Layer for Carely-AI

Handles retrieval of relevant medical information from Pinecone vector database.
Queries Pinecone using OpenAI embeddings and returns text chunks for context augmentation.
"""
import logging
from typing import List, Optional

from openai import OpenAI
from pinecone import Pinecone

# Configure logging
logger = logging.getLogger(__name__)


class RAGService:
    """
    Service layer for Retrieval-Augmented Generation (RAG) using Pinecone vector database.

    This service queries the Pinecone index to retrieve relevant medical information chunks
    based on semantic similarity to user queries.
    """

    # Configuration constants (matching insert_script.py)
    INDEX_NAME = "carely"
    NAMESPACE = "carely"
    EMBED_MODEL = "text-embedding-3-small"
    EMBED_DIMENSION = 1536

    def __init__(self, pinecone_api_key: str, openai_api_key: str):
        """
        Initialize RAG service with API keys.

        Args:
            pinecone_api_key: Pinecone API key for vector database access
            openai_api_key: OpenAI API key for embedding generation

        Raises:
            ValueError: If API keys are missing
        """
        if not pinecone_api_key:
            raise ValueError("Pinecone API key is required")
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")

        try:
            # Initialize clients
            self.openai_client = OpenAI(api_key=openai_api_key)
            self.pinecone_client = Pinecone(api_key=pinecone_api_key)

            # Connect to index
            self.index = self.pinecone_client.Index(self.INDEX_NAME)

            logger.info(f" RAG Service initialized - Index: {self.INDEX_NAME}, Namespace: {self.NAMESPACE}")
        except Exception as e:
            logger.error(f"L Failed to initialize RAG Service: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for query text using OpenAI.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.EMBED_MODEL
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def query(self, query_text: str, top_k: int = 3) -> List[str]:
        """
        Query Pinecone vector database for relevant text chunks.

        This method:
        1. Generates embedding for the query text
        2. Queries Pinecone for top_k similar vectors
        3. Extracts text chunks from metadata
        4. Returns list of relevant text chunks

        Args:
            query_text: User's query text
            top_k: Number of top results to return (default: 3)

        Returns:
            List of relevant text chunks (empty list on error or no results)
        """
        if not query_text or not query_text.strip():
            logger.warning("Empty query text provided to RAG service")
            return []

        try:
            # Generate query embedding
            logger.info(f"RAG Query: '{query_text[:100]}...' (top_k={top_k})")
            query_embedding = self._generate_embedding(query_text)

            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=self.NAMESPACE,
                include_metadata=True
            )

            # Extract text chunks from results
            chunks = []
            if results and 'matches' in results:
                for match in results['matches']:
                    score = match.get('score', 0.0)
                    metadata = match.get('metadata', {})
                    text = metadata.get('text', '')
                    source = metadata.get('source_file', 'unknown')

                    if text:
                        chunks.append(text)
                        logger.debug(f"   Match (score={score:.4f}, source={source}): {text[:100]}...")

                logger.info(f" RAG retrieved {len(chunks)} relevant chunks")
            else:
                logger.warning("No matches found in Pinecone query")

            return chunks

        except Exception as e:
            # Graceful fallback: Log error and return empty list
            logger.warning(f"�  RAG query failed (continuing without context): {e}")
            return []

    def get_context_string(self, query_text: str, top_k: int = 3) -> str:
        """
        Query RAG and return formatted context string for LLM prompts.

        Args:
            query_text: User's query text
            top_k: Number of top results to retrieve

        Returns:
            Formatted context string (empty string if no results)
        """
        chunks = self.query(query_text, top_k=top_k)

        if not chunks:
            return ""

        # Format chunks as numbered context
        context_parts = ["**Relevant Medical Information from Knowledge Base:**\n"]
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"\n**Source {i}:**\n{chunk}\n")

        return "\n".join(context_parts)

    def health_check(self) -> dict:
        """
        Check if RAG service is operational.

        Returns:
            Dictionary with health status information
        """
        try:
            # Try to get index stats
            stats = self.index.describe_index_stats()
            total_vectors = stats.get('total_vector_count', 0)
            namespace_count = stats.get('namespaces', {}).get(self.NAMESPACE, {}).get('vector_count', 0)

            return {
                "status": "healthy",
                "index": self.INDEX_NAME,
                "namespace": self.NAMESPACE,
                "total_vectors": total_vectors,
                "namespace_vectors": namespace_count
            }
        except Exception as e:
            logger.error(f"RAG health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
