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

### AI Agent System (Routing Agent as Coordinator)

The system uses a coordinator architecture where the **Routing Agent** orchestrates information flow:

```
User → Routing Agent (Coordinator)
         ├─→ QnA Agent (with RAG) → Pinecone Vector DB
         └─→ Appointment Agent (receives context from Routing Agent)
```

**Key architectural points:**

1. **Routing Agent** (`server/app/agents/routing_agent.py`):
   - Classifies user intent as "scheduling" or "q&a" using hybrid keyword stemming + LLM verification
   - Coordinates information flow between agents
   - Queries QnA Agent (which has RAG) and passes information to Appointment Agent via `get_appointment_context()`
   - Uses NLTK PorterStemmer for keyword matching, falls back to OpenAI GPT-4o-mini when confidence < 0.6

2. **QnA Agent** (`server/app/agents/qna_agent.py`):
   - Handles general medical Q&A
   - Integrates with RAG (Retrieval-Augmented Generation) when enabled
   - Provides doctor/schedule information to Routing Agent
   - Uses Pinecone vector database for knowledge retrieval

3. **Appointment Agent** (`server/app/agents/appointment_agent.py`):
   - Handles appointment booking, cancellation, rescheduling
   - Receives doctor/schedule context from Routing Agent (not direct RAG access)
   - Uses OpenAI GPT-4o-mini for natural language understanding
   - Directly creates/updates database records

**Information flow for appointments:**
- User: "I need to see a cardiologist"
- Routing Agent: Classifies as "appointment_service"
- Routing Agent: Calls `get_appointment_context()` which queries QnA Agent (RAG)
- QnA Agent: Returns doctor info from knowledge base
- Routing Agent: Passes context to Appointment Agent
- Appointment Agent: Uses context to book with real doctor information

### Backend Structure

**Entry point:** `server/app/main.py` - FastAPI application initialization

**Configuration:** `server/app/core/config.py` - Uses pydantic-settings for environment variables

**Key modules:**
- `app/api/v1/endpoints/` - API routes (auth, chat, patients, medical_records, etc.)
- `app/agents/` - AI agents (routing, qna, appointment)
- `app/models/` - SQLAlchemy database models
- `app/schemas/` - Pydantic request/response schemas
- `app/db/` - Database session and base configuration
- `RAG/` - RAG implementation (Pinecone integration, PDF processing)

**Database:** Neon serverless Postgres (with connection pooling and Alembic migrations)

**Chat endpoint flow** (`server/app/api/v1/endpoints/chat.py:68`):
1. Routing Agent classifies intent
2. If "appointment_service": Get context from Routing Agent → Appointment Agent
3. If "qna_service": QnA Agent with RAG
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

**Location:** `server/RAG/medical_rag.py`

**How it works:**
- PDF processing: Extracts and cleans text from medical PDFs
- Chunking: Splits into 120-character wrapped chunks
- Embeddings: OpenAI text-embedding-ada-002
- Vector DB: Pinecone for similarity search
- Retrieval: top_k=3 chunks for context augmentation

**Enable/Disable:**
```bash
# In server/.env
RAG_ENABLED=true  # Enable RAG
PINECONE_API_KEY=your-key
```

**QnA Agent RAG integration** (`server/app/agents/qna_agent.py`):
- Initialized with `use_rag=True` when RAG_ENABLED
- Retrieves relevant chunks before generating response
- Augments system prompt with retrieved context

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
1. Place PDFs in `server/RAG/` directory
2. Update `NUM_KNOWLEDGE_TXT` constant
3. Run embedding process (see RAG setup in docs)

**Query RAG directly:**
```python
from RAG.medical_rag import MedicalRAG
rag = MedicalRAG(api_key=settings.PINECONE_API_KEY)
results = rag.query("your question", top_k=3)
```

## Important Implementation Notes

### Agent Initialization Order

Agents MUST be initialized in this order (see `server/app/api/v1/endpoints/chat.py:48`):
1. QnA Agent (with RAG if enabled)
2. Routing Agent (with qna_agent parameter)
3. Appointment Agent (standalone)

This ensures proper dependency injection for the coordinator pattern.

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
- Verify `RAG_ENABLED=true` in server/.env
- Check PINECONE_API_KEY is set
- Look for "QnA agent initialized with RAG" in server logs

### Agent initialization errors
- Ensure OpenAI API key is valid and has credits
- Check agent initialization order (QnA → Routing → Appointment)
- Verify NLTK data is downloaded

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

**Development:**
- Python 3.11+
- Node.js 16+
- Neon Postgres (serverless, auto-scaling)
