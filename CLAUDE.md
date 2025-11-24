# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Carely-AI is an intelligent healthcare chatbot with appointment scheduling, Q&A capabilities, and RAG-enhanced responses. It features a FastAPI backend with AI agents and a React frontend.

## Development Commands

### Starting the Application

**Quick start (both server + client):**
```bash
./start_all.sh
```

**Server only (with Docker - Recommended):**
```bash
cd server
# Make sure your .env file has the Neon DATABASE_URL set
docker-compose up --build
```

**Server only (without Docker):**
```bash
cd server
bash run_server.sh
# Or manually:
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Client only:**
```bash
cd client
npm run dev
```

**Access points:**
- Client: http://localhost:5173
- Server API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Commands

**Build and start the server:**
```bash
cd server
docker-compose up --build
```

**Start without rebuilding:**
```bash
cd server
docker-compose up
```

**Stop the server:**
```bash
cd server
docker-compose down
```

**View logs:**
```bash
cd server
docker-compose logs -f
```

**Rebuild after dependency changes:**
```bash
cd server
docker-compose up --build --force-recreate
```

**Run Alembic commands in Docker:**
```bash
# Access the container shell
docker exec -it carely-api bash

# Inside the container, run Alembic commands
alembic current
alembic history
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Testing

**Server tests:**
```bash
cd server
source venv/bin/activate
bash run_tests.sh
# Or: python quick_test.py
```

**Client linting:**
```bash
cd client
npm run lint
```

### Building

**Client production build:**
```bash
cd client
npm run build
```

## Architecture

### AI Agent System (Decoupled Service Layer Architecture)

The system uses a clean, decoupled architecture where each agent has a single responsibility:

```
User → Chat Endpoint
         ↓
    Routing Agent (Pure Intent Classifier)
         ↓
    ┌────┴────────┐
    ↓             ↓
QnA Agent    Appointment Agent
    ↓
RAG Service → Pinecone Vector DB
```

**Key architectural points:**

1. **Routing Agent** (`server/app/agents/routing_agent.py`):
   - Pure intent classifier - NO coordination logic
   - Classifies user intent as "scheduling" or "qna" using hybrid keyword stemming + LLM verification
   - Uses NLTK PorterStemmer for keyword matching, falls back to OpenAI GPT-4o-mini when confidence < 0.6
   - Returns routing decision with `next_service` (either "appointment_service" or "qna_service")

2. **RAG Service** (`server/app/service/rag_service.py`):
   - Service layer for Pinecone vector database queries
   - `query(query_text, top_k=3)` - Generates embeddings and retrieves relevant chunks
   - `get_context_string()` - Formats chunks for LLM prompts
   - Graceful fallback: Returns empty list on errors, logs warnings
   - Configuration: Index "carely", Namespace "carely", Model "text-embedding-3-small"

3. **QnA Agent** (`server/app/agents/qna_agent.py`):
   - Handles general medical Q&A with optional RAG integration
   - `generate_response(user_message, conversation_history)` - Main entry point
   - Queries RAG service for relevant medical knowledge (if `use_rag=True`)
   - Builds system prompt with RAG context and calls OpenAI GPT-4o-mini
   - Graceful fallback: Continues without RAG context if service fails

4. **Appointment Agent** (`server/app/agents/appointment_agent.py`):
   - Handles appointment booking, cancellation, rescheduling
   - Uses OpenAI GPT-4o-mini with function calling for natural language understanding
   - Directly queries Provider database for doctor information
   - Creates/updates database records independently (no RAG dependency)

**Information flow for Q&A:**
- User: "Can I take antibiotics with alcohol?"
- Routing Agent: Classifies as "qna_service"
- Chat Endpoint: Routes to QnA Agent
- QnA Agent: Queries RAG Service for relevant medical FAQs
- RAG Service: Returns top 3 relevant chunks from Pinecone
- QnA Agent: Builds context and calls OpenAI with augmented prompt
- Returns RAG-enhanced medical information

**Information flow for appointments:**
- User: "I need to see a cardiologist"
- Routing Agent: Classifies as "appointment_service"
- Chat Endpoint: Routes to Appointment Agent
- Appointment Agent: Uses function calling to search Provider database
- Appointment Agent: Books appointment with real doctor information

### Backend Structure

**Entry point:** `server/app/main.py` - FastAPI application initialization

**Configuration:** `server/app/core/config.py` - Uses pydantic-settings for environment variables

**Key modules:**
- `app/api/v1/endpoints/` - API routes (auth, chat, patients, medical_records, etc.)
- `app/agents/` - AI agents (routing, qna, appointment)
- `app/service/` - Service layer (rag_service.py for Pinecone queries)
- `app/models/` - SQLAlchemy database models
- `app/schemas/` - Pydantic request/response schemas
- `app/db/` - Database session and base configuration
- `app/rag/` - RAG utilities (insert_script.py for PDF processing and indexing)

**Database:** Neon serverless Postgres (with connection pooling and Alembic migrations)

**Chat endpoint flow** (`server/app/api/v1/endpoints/chat.py:68`):
1. Routing Agent classifies intent (returns "appointment_service" or "qna_service")
2. If "appointment_service": Route to Appointment Agent
3. If "qna_service": Route to QnA Agent (queries RAG Service if enabled)
4. Else: General medical assistant fallback
5. Store messages in ChatMessage/ChatConversation models

### Frontend Structure

**Framework:** React 18 + Vite + TypeScript

**UI Library:** Shadcn/ui (Radix UI primitives + Tailwind CSS)

**Key components:**
- `client/src/pages/Chat.tsx` - Main chat interface
- `client/src/pages/Auth.tsx` - Login/registration
- `client/src/components/ChatMessage.tsx` - Message display with appointment cards
- `client/src/utils/api.ts` - API client with authentication

**Routing:** React Router v6 (`client/src/App.tsx`)

### RAG System

**Architecture:**
- **RAG Service** (`server/app/service/rag_service.py`) - Query layer for retrieval
- **Insert Script** (`server/app/rag/insert_script.py`) - PDF processing and indexing

**How it works:**

**1. Indexing (one-time setup):**
- PDF processing: Extracts and cleans text from medical PDFs in `server/app/rag/context/`
- Chunking: Wraps text to 120 characters, splits into 9-line chunks with 3-line overlap
- Embeddings: OpenAI text-embedding-3-small (1536 dimensions)
- Vector DB: Pinecone (index: "carely", namespace: "carely")
- Run: `python app/rag/insert_script.py`

**2. Retrieval (runtime):**
- RAG Service queries Pinecone with user question
- Generates embedding for query text
- Retrieves top_k=3 most relevant chunks
- Returns text chunks to QnA Agent

**Enable/Disable:**
```bash
# In server/.env
RAG_ENABLED=true  # Enable RAG
PINECONE_API_KEY=your-pinecone-key
```

**QnA Agent RAG integration** (`server/app/agents/qna_agent.py`):
- Initialized with `use_rag=settings.RAG_ENABLED` in chat.py
- Calls `rag_service.get_context_string(user_message)` to retrieve relevant chunks
- Augments system prompt with retrieved context
- Graceful fallback: Continues without RAG if service fails

## Environment Configuration

### Server `.env` (required)

```bash
# Required
OPENAI_API_KEY=sk-proj-your-key-here

# Optional (for RAG)
PINECONE_API_KEY=your-pinecone-key
RAG_ENABLED=true

# Application
SECRET_KEY=your-secret-key
DEBUG=True

# Database - Neon Serverless Postgres
# Use the POOLED connection string from Neon dashboard
DATABASE_URL=postgresql://username:password@ep-xxxxx-pooler.region.aws.neon.tech/carely?sslmode=require

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

**IMPORTANT:**
- The server requires `OPENAI_API_KEY` to start
- Use the **pooled** Neon connection string for optimal performance with serverless Postgres

## Database Models

Key models in `server/app/models/`:

- `Patient` - User accounts (with authentication)
- `Appointment` - Scheduled appointments (linked to patients)
- `ChatConversation` - Conversation sessions
- `ChatMessage` - Individual messages (role: user/assistant)
- `MedicalRecord` - Patient medical history
- `SupportTicket` - Support requests
- `Provider` - Healthcare providers/doctors

**Model relationships:**
- Patient 1:N Appointments
- Patient 1:N ChatConversations
- ChatConversation 1:N ChatMessages

**Boolean fields:** Models use native Postgres Boolean type (not Integer 0/1):
- `patient.is_active` - Boolean, default=True
- `appointment.is_virtual` - Boolean, default=False
- `appointment.reminder_sent` - Boolean, default=False
- `medical_record.follow_up_required` - Boolean, default=False
- `provider.is_active` - Boolean, default=True

## Database Migrations (Alembic)

**Create a new migration:**
```bash
cd server
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations:**
```bash
cd server
alembic upgrade head
```

**Rollback one migration:**
```bash
cd server
alembic downgrade -1
```

**Check current migration:**
```bash
cd server
alembic current
```

**View migration history:**
```bash
cd server
alembic history
```

**IMPORTANT:** Tables are created via Alembic migrations, not `Base.metadata.create_all()`. After cloning the repo or changing DATABASE_URL, run `alembic upgrade head` to create/update tables.

## Common Development Tasks

### Adding a new API endpoint

1. Create endpoint in `server/app/api/v1/endpoints/your_endpoint.py`
2. Add router to `server/app/api/v1/api.py`
3. Create Pydantic schemas in `server/app/schemas/`
4. Update models if needed in `server/app/models/`

### Modifying AI Agent Behavior

**Routing Agent keywords:** Edit `DEFAULT_INTENT_KEYWORDS` in `server/app/agents/routing_agent.py:46`

**QnA Agent system prompt:** Modify prompt in `server/app/agents/qna_agent.py`

**Appointment Agent:** Edit `APPOINTMENT_TYPES` and `DOCTORS` lists in `server/app/agents/appointment_agent.py`

### Working with RAG

**Add documents to knowledge base:**
1. Place PDFs in `server/app/rag/context/` directory
2. Run indexing script: `cd server && python app/rag/insert_script.py`
3. Script automatically processes all PDFs and upserts to Pinecone

**Query RAG directly (for testing):**
```python
from app.service.rag_service import RAGService
from app.core.config import settings

rag = RAGService(
    pinecone_api_key=settings.PINECONE_API_KEY,
    openai_api_key=settings.OPENAI_API_KEY
)
chunks = rag.query("your question", top_k=3)
# Or get formatted context:
context = rag.get_context_string("your question", top_k=3)
```

**Check RAG health:**
```python
health = rag.health_check()
print(health)  # Shows index stats, vector counts, etc.
```

## Important Implementation Notes

### Agent Initialization Order

Agents are initialized in this order (see `server/app/api/v1/endpoints/chat.py:48`):
1. QnA Agent (with `use_rag=settings.RAG_ENABLED`)
2. Routing Agent (pure intent classifier, no dependencies)
3. Appointment Agent (standalone, queries Provider database)

**Note:** The initialization order is flexible since agents are now decoupled. The Routing Agent no longer requires a reference to the QnA Agent.

### Service Layer Pattern

The RAG functionality is implemented as a **service layer** to promote separation of concerns:

**Benefits:**
- **Reusability:** RAG service can be used by any component (not just QnA agent)
- **Testability:** Service can be unit tested independently
- **Maintainability:** Pinecone logic isolated in one place
- **Flexibility:** Easy to swap vector databases or add caching

**Architecture:**
```
QnA Agent (business logic)
    ↓ calls
RAG Service (data access layer)
    ↓ queries
Pinecone Vector DB (data storage)
```

**Key principle:** Agents contain business logic (prompt building, LLM calls), services contain data access logic (database/API queries).

### Graceful Degradation

The system is designed to gracefully handle failures:

**RAG Service failures:**
- Returns empty list instead of throwing exceptions
- Logs warnings but doesn't crash
- QnA agent continues without context (falls back to general knowledge)

**QnA Agent failures:**
- Chat endpoint falls back to general medical assistant
- User still gets a response (even if not RAG-enhanced)

**Configuration flexibility:**
- `RAG_ENABLED=false` - System works without RAG
- Missing PINECONE_API_KEY - QnA agent disables RAG automatically
- Missing PDFs in context/ - Insert script reports error gracefully

### Authentication

All `/api/v1/*` endpoints (except auth) require JWT Bearer token.

**Getting a token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

Use token in subsequent requests:
```bash
curl http://localhost:8000/api/v1/patients/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### NLTK Data

The Routing Agent uses NLTK for stemming. On first run, download required data:
```python
import nltk
nltk.download('punkt')
```

This is handled automatically by the agent, but may require internet access on first initialization.

## Troubleshooting

### "OPENAI_API_KEY not configured"
- Check `server/.env` file exists and contains key
- Use absolute path: `cat server/.env | grep OPENAI_API_KEY`

### Port conflicts
```bash
# Kill process on port 8000 (server)
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173 (client)
lsof -ti:5173 | xargs kill -9
```

### RAG not working

**Check configuration:**
```bash
cd server
grep RAG_ENABLED .env  # Should show: RAG_ENABLED=true
grep PINECONE_API_KEY .env  # Should show your key
```

**Check server logs on startup:**
```
✅ RAG Service initialized - Index: carely, Namespace: carely
✅ QnA Agent initialized (RAG: True)
```

**If RAG service fails to initialize:**
- Check Pinecone API key is valid
- Verify Pinecone index "carely" exists (run `python app/rag/insert_script.py`)
- Check network connectivity to Pinecone

**If no results returned:**
- Verify PDFs have been indexed: Check Pinecone dashboard for vector count
- Try test query: `rag.health_check()` should show namespace_vectors > 0
- Check if query is too specific - try broader medical terms

**Common issues:**
- `⚠️ Failed to initialize RAG service` - API key invalid or network error
- `⚠️ RAG query failed` - Pinecone connection issue (graceful fallback active)
- Empty responses - No PDFs indexed or query doesn't match content

### Agent initialization errors
- Ensure OpenAI API key is valid and has credits
- Agent initialization order is now flexible (agents are decoupled)
- Verify NLTK data is downloaded for Routing Agent

### Database connection issues
**"relation does not exist" errors:**
```bash
cd server
alembic upgrade head  # Apply migrations to create tables
```

**"could not connect to server" errors:**
- Verify Neon connection string in `.env` is correct
- Check that you're using the **pooled** connection string
- Ensure `sslmode=require` is in the connection string
- Verify Neon database is not suspended (auto-suspends after inactivity)

**Migration conflicts:**
```bash
cd server
alembic current        # Check current migration
alembic history        # View migration history
alembic downgrade -1   # Rollback if needed
```

## Tech Stack Summary

**Backend:**
- FastAPI (web framework)
- SQLAlchemy (ORM) + Alembic (migrations)
- Neon serverless Postgres (database)
- psycopg2-binary (Postgres driver)
- OpenAI GPT-4o-mini (LLM)
- NLTK (NLP, stemming)
- Pinecone (vector database)
- JWT (authentication)

**Frontend:**
- React 18 + Vite
- TypeScript
- Shadcn/ui (Radix UI + Tailwind)
- React Router v6
- React Query (TanStack Query)
