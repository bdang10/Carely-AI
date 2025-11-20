# Routing Agent Overview

The routing agent mirrors the `AgentLogic1` logic from the exploratory notebook (`agentv1_ipynb_v1_6.ipynb`). Its job is to classify every inbound chat message as either **Scheduling** or **Q&A** (or fall back to a `user_decision` guard) and inform the backend which downstream agent should handle the turn.

## Architecture

- **Keyword / stemming phase**  
  Uses `nltk.PorterStemmer` plus curated keyword lists (same as the notebook) to count hits for Scheduling vs Q&A.
- **LLM verification**  
  If the keyword confidence is below `0.6`, the agent calls OpenAI (`gpt-4o-mini`) with the exact JSON schema defined in the notebook. Invalid JSON gracefully downgrades to `user_decision`.
- **Routing output**  
  The agent returns intent, confidence, action hints, and the raw schema result. This metadata is now surfaced in `ChatMessageResponse.routing_decision`.

## Runtime Flow

1. `app/api/v1/endpoints/chat.py` instantiates:
   - `RoutingAgent` for intent detection
   - `QnaAgent` for the general medical assistant prompt
   - `AppointmentAgent` (existing)
2. On every `/chat` request the router runs first.
3. Based on the router output:
   - `appointment_service` → `AppointmentAgent.process_appointment_request`
   - `qna_service` → `QnaAgent.generate_response`
   - Fallback → legacy general assistant prompt
4. Chat responses now include both `appointment_data` (when applicable) and the router metadata for observability.

## Testing

- Quick manual smoke test: run `python quick_test.py` after setting `OPENAI_API_KEY`, then POST to `/api/v1/chat` with sample scheduling and Q&A prompts to observe `routing_decision`.
- Unit tests can inject a `RoutingAgent` with `openai_client=None` to exercise the stemming-only path without external calls.


