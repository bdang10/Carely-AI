"""
Lightweight wrapper around the general medical assistant prompt used by /chat.
This allows the chat endpoint to treat Q&A interactions as a dedicated agent.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from openai import OpenAI


class QnaAgent:
    """Handles general medical Q&A interactions via OpenAI."""

    _SYSTEM_PROMPT = (
        "You are a knowledgeable and responsible medical assistant. "
        "Provide clear, concise, medically accurate answers. "
        "Include disclaimers when appropriate and recommend consulting "
        "healthcare professionals for diagnostic or treatment decisions."
    )



    def __init__(
        self,
        openai_client: OpenAI,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,) -> None:
        if not openai_client:
            raise ValueError("QnaAgent requires a configured OpenAI client.")

        self.client = openai_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Run the general assistant prompt with the provided conversation history."""
        history = conversation_history or []
        messages = [{"role": "system", "content": self._SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()


