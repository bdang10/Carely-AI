"""
QnA Agent for Carely-AI

Handles general medical Q&A with optional RAG (Retrieval-Augmented Generation) support.
Integrates with RAG service to provide context-aware medical information.
"""
import logging
from typing import List, Dict, Optional

from openai import OpenAI

from app.core.config import settings
from app.service.rag_service import RAGService

# Configure logging
logger = logging.getLogger(__name__)


class QnaAgent:
    """
    AI Agent for handling medical Q&A questions with optional RAG enhancement.

    This agent:
    1. Optionally queries RAG service for relevant medical knowledge
    2. Builds context from retrieved information
    3. Generates responses using OpenAI with augmented context
    """

    def __init__(self, openai_client: OpenAI, use_rag: bool = False):
        """
        Initialize QnA Agent.

        Args:
            openai_client: OpenAI client for LLM calls
            use_rag: Whether to enable RAG for knowledge retrieval
        """
        self.client = openai_client
        self.use_rag = use_rag
        self.rag_service: Optional[RAGService] = None

        # Initialize RAG service if enabled
        if self.use_rag:
            if settings.PINECONE_API_KEY and settings.OPENAI_API_KEY:
                try:
                    self.rag_service = RAGService(
                        pinecone_api_key=settings.PINECONE_API_KEY,
                        openai_api_key=settings.OPENAI_API_KEY
                    )
                    logger.info(" QnA Agent initialized with RAG enabled")
                except Exception as e:
                    logger.warning(f"�  Failed to initialize RAG service: {e}")
                    logger.warning("   QnA Agent will continue without RAG")
                    self.use_rag = False
            else:
                logger.warning("�  RAG enabled but API keys missing. RAG disabled.")
                self.use_rag = False
        else:
            logger.info(" QnA Agent initialized without RAG")

    def _build_system_prompt(self, rag_context: Optional[str] = None) -> str:
        """
        Build system prompt for medical Q&A, optionally including RAG context.

        Args:
            rag_context: Retrieved context from RAG service (if available)

        Returns:
            System prompt string
        """
        base_prompt = """You are a knowledgeable and empathetic medical information assistant for Carely Healthcare.

Your role is to:
- Provide clear, accurate, and helpful medical information
- Answer questions about symptoms, conditions, medications, and general health topics
- Help users understand medical concepts in accessible language
- Guide users on when to seek professional medical care
- Provide information about hospital services, policies, and procedures

IMPORTANT Guidelines:
- You provide information and guidance, NOT medical diagnoses or treatment prescriptions
- Always emphasize that users should consult healthcare professionals for:
  * Specific diagnoses
  * Treatment decisions
  * Medication prescriptions
  * Serious or urgent medical concerns
- Be warm, supportive, and maintain patient confidentiality
- If you don't know something, be honest and suggest consulting a healthcare provider
- For appointment scheduling requests, direct users to use the appointment system

When answering questions:
1. Provide clear, accurate information based on established medical knowledge
2. Use accessible language while maintaining medical accuracy
3. Include important safety information and red flags
4. Encourage appropriate medical consultation when needed
"""

        # Add RAG context if available
        if rag_context:
            base_prompt += f"\n\n{rag_context}\n"
            base_prompt += """
**Instructions for using the knowledge base:**
- Prioritize information from the knowledge base sources above
- Cite or reference the provided information when relevant
- If the knowledge base doesn't contain relevant information, use your general medical knowledge
- Always maintain the empathetic and helpful tone
"""

        base_prompt += """
Remember: You are an information resource, not a replacement for professional medical advice, diagnosis, or treatment.
"""

        return base_prompt

    def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response to a medical Q&A question.

        Args:
            user_message: The user's question
            conversation_history: Optional conversation history for context

        Returns:
            AI-generated response string
        """
        if not user_message or not user_message.strip():
            return "I'd be happy to help! Please ask your medical question."

        try:
            # Step 1: Query RAG service if enabled
            rag_context = None
            if self.use_rag and self.rag_service:
                logger.info(f"Querying RAG for: '{user_message[:100]}...'")
                rag_context = self.rag_service.get_context_string(user_message, top_k=3)

                if rag_context:
                    logger.info(f" RAG context retrieved ({len(rag_context)} characters)")
                else:
                    logger.info("9  No RAG context found, using general knowledge")

            # Step 2: Build system prompt with RAG context
            system_prompt = self._build_system_prompt(rag_context)

            # Step 3: Build messages for OpenAI
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Step 4: Call OpenAI API
            logger.info(f"> Generating response with OpenAI (RAG context: {bool(rag_context)})")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            ai_response = response.choices[0].message.content.strip()
            logger.info(f" Generated response ({len(ai_response)} characters)")

            return ai_response

        except Exception as e:
            logger.error(f"L Error generating QnA response: {e}")
            # Graceful fallback
            return (
                "I apologize, but I'm having trouble processing your question right now. "
                "Please try again in a moment, or contact our support team if the issue persists. "
                "For urgent medical concerns, please call your healthcare provider or emergency services."
            )

    def health_check(self) -> dict:
        """
        Check if QnA agent is operational.

        Returns:
            Dictionary with health status information
        """
        status = {
            "agent": "QnaAgent",
            "status": "healthy",
            "rag_enabled": self.use_rag,
            "rag_available": self.rag_service is not None
        }

        # Add RAG service health if available
        if self.rag_service:
            try:
                rag_health = self.rag_service.health_check()
                status["rag_service"] = rag_health
            except Exception as e:
                status["rag_service"] = {"status": "unhealthy", "error": str(e)}

        return status
