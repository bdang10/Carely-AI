"""
Lightweight wrapper around the general medical assistant prompt used by /chat.
This allows the chat endpoint to treat Q&A interactions as a dedicated agent.
Enhanced with optional RAG (Retrieval-Augmented Generation) capability.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

# Add RAG directory to path if it exists
RAG_DIR = Path(__file__).parent.parent.parent / "RAG"
if RAG_DIR.exists():
    sys.path.insert(0, str(RAG_DIR))


class QnaAgent:
    """Handles general medical Q&A interactions via OpenAI with optional RAG support."""

    _SYSTEM_PROMPT = (
        "You are a knowledgeable and responsible medical assistant. "
        "Provide clear, concise, medically accurate answers. "
        "Include disclaimers when appropriate and recommend consulting "
        "healthcare professionals for diagnostic or treatment decisions."
    )

    _SYSTEM_PROMPT_WITH_RAG = (
        "You are a knowledgeable and responsible medical assistant for Carely Healthcare. "
        "Provide clear, concise, medically accurate answers based on the provided medical knowledge. "
        "When relevant medical knowledge is provided in the context (marked with ########), "
        "use it as your primary source of information. This knowledge comes from our hospital's "
        "official documentation and should be prioritized. "
        "Include disclaimers when appropriate and recommend consulting "
        "healthcare professionals for diagnostic or treatment decisions."
    )

    def __init__(
        self,
        openai_client: OpenAI,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_rag: bool = False,
    ) -> None:
        if not openai_client:
            raise ValueError("QnaAgent requires a configured OpenAI client.")

        self.client = openai_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_rag = use_rag
        self.rag_instance = None
        
        # Initialize RAG if enabled
        if self.use_rag:
            try:
                # Ensure environment variables are set for RAG
                import os
                from app.core.config import settings
                
                # Set environment variables if not already set (RAG needs them)
                if not os.getenv("OPENAI_API_KEY") and settings.OPENAI_API_KEY:
                    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
                if not os.getenv("PINECONE_API_KEY") and settings.PINECONE_API_KEY:
                    os.environ["PINECONE_API_KEY"] = settings.PINECONE_API_KEY
                
                from medical_rag import RAG
                print("🔧 Initializing RAG system...")
                self.rag_instance = RAG()
                print("✅ RAG system initialized successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize RAG: {e}")
                print("   Falling back to standard QnA mode")
                self.use_rag = False

    def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate response with optional RAG enhancement.
        
        If RAG is enabled and initialized, it will retrieve relevant medical knowledge
        before generating the response.
        """
        # Use RAG if available
        if self.use_rag and self.rag_instance:
            try:
                print(f"🔍 Using RAG to answer: {user_message[:50]}...")
                response = self.rag_instance.query_RAG(user_message)
                return response + "\n\n📚 *Response enhanced with medical knowledge base.*"
            except Exception as e:
                print(f"⚠️  RAG query failed: {e}, falling back to standard mode")
                # Fall through to standard response
        
        # Standard response without RAG
        history = conversation_history or []
        system_prompt = self._SYSTEM_PROMPT_WITH_RAG if self.use_rag else self._SYSTEM_PROMPT
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()


