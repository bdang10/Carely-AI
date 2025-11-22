# Quick Start Guide

## ✅ Architecture

The system uses a **Routing Agent as Coordinator** architecture:

```
User → Routing Agent (Coordinator)
           ├─→ QnA Agent (with RAG) → Knowledge Base
           └─→ Appointment Agent (receives context)
```

**Key Point:** The Routing Agent coordinates information flow. It queries the QnA Agent (which has RAG) and passes that information to the Appointment Agent.

---

## 🚀 How to Run

### 1. Start the Server

```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server
bash run_server.sh
```

**Expected logs:**
```
✅ QnA agent initialized with RAG
✅ Routing agent initialized with QnA agent  
✅ Appointment agent initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start the Client

```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/client
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in XXX ms
➜  Local:   http://localhost:5173/
```

### 3. Test the System

Open browser to `http://localhost:5173`

**Test 1: Q&A (uses RAG directly)**
```
You: "What services does the hospital provide?"
AI: [Response using RAG knowledge base]
```

**Test 2: Appointment (uses RAG via Routing Agent)**
```
You: "I need to see a cardiologist"

System logs should show:
🔄 Getting appointment context from Routing Agent...
🔄 Routing Agent: Requesting doctor information from QnA Agent...
✅ Routing Agent: Received doctor information from QnA Agent
✅ Context received: ['doctor_info', 'schedule_info']

AI: "We have these cardiologists available:
- Dr. Michael Chen (Mon-Fri 9AM-5PM)  
- Dr. Sarah Williams (Tue-Sat 8AM-4PM)
Which would you prefer?"
```

**Test 3: Book Appointment**
```
You: "Book with Dr. Chen tomorrow at 10am for a heart checkup"

AI: [Books appointment using real doctor information from RAG]
```

---

## 🔧 Configuration

### Required Environment Variables

**In `/Users/arvindrangarajan/PythonLab/Carely-AI/server/.env`:**

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-your-key-here

# RAG Configuration (required for knowledge base)
RAG_ENABLED=true
PINECONE_API_KEY=your-pinecone-key-here

# Database
DATABASE_URL=sqlite:///./carely.db

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Enable/Disable RAG

**To enable RAG (recommended):**
```bash
RAG_ENABLED=true
```

**To disable RAG (fallback mode):**
```bash
RAG_ENABLED=false
```

---

## 🏗️ How It Works

### Information Flow for Appointments:

1. **User asks for appointment**
   ```
   "I need to see a cardiologist"
   ```

2. **Routing Agent classifies intent**
   ```
   → "appointment_service"
   ```

3. **Routing Agent queries QnA Agent**
   ```python
   context = routing_agent.get_appointment_context()
   # QnA Agent uses RAG to get doctor information
   ```

4. **Routing Agent provides context to Appointment Agent**
   ```python
   appointment_agent.process_appointment_request(
       ...,
       context=context  # Doctor info from RAG
   )
   ```

5. **Appointment Agent uses context**
   ```
   - Builds system prompt with doctor information
   - AI responds with real doctor names and schedules
   - Books appointment with accurate information
   ```

---

## 🧪 Debugging

### Check Server Logs

When you make an appointment request, you should see:

```
🔄 Getting appointment context from Routing Agent...
🔄 Routing Agent: Requesting doctor information from QnA Agent...
✅ Routing Agent: Received doctor information from QnA Agent
✅ Context received: ['doctor_info', 'schedule_info']
```

If you don't see these logs:
- ❌ RAG may not be enabled (check `RAG_ENABLED=true` in `.env`)
- ❌ Routing Agent may not have QnA Agent
- ❌ Check for errors in server startup

### Verify Architecture

```python
# In Python console:
from openai import OpenAI
from app.core.config import settings
from app.agents.qna_agent import QnaAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.appointment_agent import AppointmentAgent

client = OpenAI(api_key=settings.OPENAI_API_KEY)

qna = QnaAgent(client, use_rag=True)
routing = RoutingAgent(client, qna_agent=qna)
appointment = AppointmentAgent(client)

print(f"✓ QnA has RAG: {qna.rag_instance is not None}")
print(f"✓ Routing has QnA: {routing.qna_agent is not None}")
print(f"✓ Appointment standalone: {not hasattr(appointment, 'qna_agent')}")
```

---

## 📚 Documentation

- **`FINAL_ARCHITECTURE.md`** - Complete architecture overview
- **`ROUTING_AGENT_COORDINATOR.md`** - Detailed coordination flow
- **`HOW_TO_USE_RAG.md`** - RAG setup and usage
- **`API_KEY_AUDIT.md`** - API key configuration

---

## ✅ What to Expect

### When RAG is Enabled:

**Q&A Queries:**
- ✅ Accurate answers from knowledge base
- ✅ Responses include hospital-specific information
- ✅ Citations from documents

**Appointment Queries:**
- ✅ Real doctor names and specialties
- ✅ Accurate schedules
- ✅ Hospital-specific appointment information
- ✅ Coordinated through Routing Agent

### When RAG is Disabled:

**Q&A Queries:**
- ⚠️  Generic responses from OpenAI
- ⚠️  No hospital-specific information

**Appointment Queries:**
- ⚠️  Basic appointment functionality
- ⚠️  Generic doctor information
- ⚠️  Still works, but less accurate

---

## 🎯 Key Features

### 1. Routing Agent Coordinates
- Classifies user intent
- Queries QnA Agent for information
- Provides context to Appointment Agent
- Central orchestrator

### 2. QnA Agent with RAG
- Retrieves information from knowledge base
- Provides information to Routing Agent
- Can also handle Q&A requests directly

### 3. Appointment Agent
- Receives context from Routing Agent
- Uses RAG information (via Routing Agent)
- Books appointments with accurate data
- No direct dependencies

---

## 🚀 Ready to Use!

1. ✅ Start server: `bash run_server.sh`
2. ✅ Start client: `npm run dev`
3. ✅ Open browser: `http://localhost:5173`
4. ✅ Test appointments and Q&A

**The system is ready!** The Routing Agent will coordinate all information flow, querying the QnA Agent (with RAG) and providing context to the Appointment Agent. 🎉
