# Carely-AI Healthcare Assistant

An intelligent healthcare chatbot with appointment scheduling, Q&A capabilities, and RAG-enhanced responses.

---

## 🚀 Quick Start

### Option 1: One Command (Easiest)

```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI
./start_all.sh
```

This starts both server and client automatically!

### Option 2: Manual (Two Terminals)

**Terminal 1 - Server:**
```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server
bash run_server.sh
```

**Terminal 2 - Client:**
```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/client
npm run dev
```

---

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Client App** | http://localhost:5173 | Main web interface |
| **Server API** | http://localhost:8000 | Backend API |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/api/v1/health | Server health status |

---

## 📁 Project Structure

```
Carely-AI/
├── server/              # FastAPI Backend
│   ├── app/
│   │   ├── agents/      # AI Agents (Routing, QnA, Appointment)
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Configuration & security
│   │   ├── db/          # Database models & session
│   │   ├── models/      # SQLAlchemy models
│   │   └── schemas/     # Pydantic schemas
│   ├── RAG/             # RAG implementation (medical knowledge base)
│   ├── venv/            # Python virtual environment
│   ├── requirements.txt # Python dependencies
│   └── run_server.sh    # Server startup script
│
├── client/              # React + Vite Frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── pages/       # Page components
│   │   └── utils/       # API utilities
│   ├── node_modules/    # Node dependencies
│   ├── package.json     # Node dependencies config
│   └── vite.config.ts   # Vite configuration
│
├── start_all.sh         # Launch both server & client
└── HOW_TO_RUN.md        # Detailed running instructions
```

---

## ✨ Features

### 🤖 AI Agents
- **Routing Agent**: Intelligently routes queries to scheduling or Q&A
- **Appointment Agent**: Handles appointment booking, cancellation, rescheduling
- **QnA Agent**: Answers medical questions with RAG support

### 📅 Appointment Management
- Book appointments with specific doctors
- View all appointments
- Cancel appointments
- Reschedule appointments
- Available time slot suggestions

### 💬 Chat Interface
- Natural language conversations
- Context-aware responses
- Conversation history
- Multi-turn dialogues

### 📚 RAG (Optional)
- Retrieval-Augmented Generation for accurate medical information
- Pinecone vector database integration
- Hospital-specific knowledge base

---

## 🔧 Configuration

### Server Environment Variables

Create `.env` file in `server/` directory:

```bash
# Required
OPENAI_API_KEY=sk-proj-your-key-here

# Optional (for RAG)
PINECONE_API_KEY=your-pinecone-key-here
RAG_ENABLED=true

# Application
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///./carely.db

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [HOW_TO_RUN.md](HOW_TO_RUN.md) | Complete guide to running server & client |
| [server/README.md](server/README.md) | Server-specific documentation |
| [server/QUICK_START.md](server/QUICK_START.md) | Quick server setup guide |
| [server/TEST_GUIDE.md](server/TEST_GUIDE.md) | Testing documentation |
| [server/API_KEY_AUDIT.md](server/API_KEY_AUDIT.md) | API key configuration audit |
| [server/RAG_SETUP_GUIDE.md](server/RAG_SETUP_GUIDE.md) | RAG integration guide |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI
- **AI/ML**: OpenAI GPT-4o-mini
- **Database**: SQLite (SQLAlchemy ORM)
- **Authentication**: JWT tokens
- **NLP**: NLTK (for intent classification)
- **RAG**: Pinecone (vector database)

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **UI Library**: Shadcn/ui (Radix UI + Tailwind CSS)
- **Routing**: React Router
- **State Management**: React Query
- **HTTP Client**: Axios

---

## 🧪 Testing

### Test Server

```bash
cd server
source venv/bin/activate

# Run all tests
bash run_tests.sh

# Test RAG integration
python test_rag_integration.py

# Test API key loading
python test_openai_key.py
```

### Test Client

```bash
cd client
npm run lint
```

---

## 🐛 Troubleshooting

### Server Issues

**"OPENAI_API_KEY not configured"**
```bash
# Check .env file
cat server/.env | grep OPENAI_API_KEY
# Add if missing
echo "OPENAI_API_KEY=your-key" >> server/.env
```

**"Port 8000 already in use"**
```bash
lsof -ti:8000 | xargs kill -9
```

### Client Issues

**"Cannot connect to server"**
- Ensure server is running on http://localhost:8000
- Check CORS settings in server `.env`

**"Port 5173 already in use"**
```bash
lsof -ti:5173 | xargs kill -9
```

### Common Issues

**See full troubleshooting guide**: [HOW_TO_RUN.md](HOW_TO_RUN.md#troubleshooting)

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/ping` | Health check |
| GET | `/api/v1/health` | Detailed health status |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/chat` | Send chat message |
| GET | `/api/v1/patients/me` | Get current user |
| GET | `/docs` | Interactive API documentation |

Full API documentation: http://localhost:8000/docs

---

## 👥 Development Team

Built as part of a healthcare AI project.

---

## 📄 License

See [LICENSE](LICENSE) file for details.

---

## 🎯 Next Steps

1. **First time?** See [HOW_TO_RUN.md](HOW_TO_RUN.md) for setup
2. **Want to test?** See [server/TEST_GUIDE.md](server/TEST_GUIDE.md)
3. **Need RAG?** See [server/RAG_SETUP_GUIDE.md](server/RAG_SETUP_GUIDE.md)
4. **API details?** Visit http://localhost:8000/docs after starting

---

**Ready to start?**

```bash
./start_all.sh
```

🎉 **Enjoy using Carely-AI!**

