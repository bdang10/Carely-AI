# How to Run Carely-AI (Server + Client)

Complete guide to start the Carely-AI Healthcare Assistant application.

---

## 🚀 Quick Start (Both Server & Client)

### Terminal 1: Start the Server

```bash
# Navigate to server directory
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server

# Run the server
bash run_server.sh
```

### Terminal 2: Start the Client

```bash
# Navigate to client directory  
cd /Users/arvindrangarajan/PythonLab/Carely-AI/client

# Start the client
npm run dev
```

**Then open:** http://localhost:5173

---

## 📋 Detailed Instructions

### Prerequisites

#### Server Requirements:
- ✅ Python 3.11+
- ✅ Virtual environment (`venv`)
- ✅ OpenAI API Key in `.env`

#### Client Requirements:
- ✅ Node.js 16+ and npm
- ✅ Dependencies installed

---

## 🖥️ Server Setup & Run

### Step 1: Check Environment

```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server

# Check .env file exists
ls -la .env

# Verify API key is set (should show key)
grep OPENAI_API_KEY .env
```

### Step 2: Activate Virtual Environment

```bash
# Activate the server's venv
source venv/bin/activate

# Verify activation (should see (venv) in prompt)
which python
# Should show: /Users/arvindrangarajan/PythonLab/Carely-AI/server/venv/bin/python
```

### Step 3: Install Dependencies (First Time Only)

```bash
# Only if you haven't installed dependencies yet
pip install -r requirements.txt

# For RAG support (optional)
pip install pinecone-client pymupdf scikit-learn
```

### Step 4: Start the Server

```bash
# Option 1: Using the helper script (recommended)
bash run_server.sh

# Option 2: Direct uvicorn command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Verify Server is Running

You should see:
```
🚀 Starting Carely AI Backend Server...
📖 API Documentation: http://localhost:8000/docs
🔧 Alternative Docs: http://localhost:8000/redoc

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test it:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Root: http://localhost:8000

---

## 🎨 Client Setup & Run

### Step 1: Navigate to Client Directory

```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/client
```

### Step 2: Install Dependencies (First Time Only)

```bash
# Check if node_modules exists
ls node_modules

# If not, install dependencies
npm install
```

### Step 3: Start the Client

```bash
# Start development server
npm run dev
```

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### Step 4: Open in Browser

Open: **http://localhost:5173**

---

## 🔧 Troubleshooting

### Server Issues

#### Issue: "OPENAI_API_KEY not found"
```bash
# Check .env file
cat /Users/arvindrangarajan/PythonLab/Carely-AI/server/.env | grep OPENAI_API_KEY

# If missing, add it:
echo "OPENAI_API_KEY=your-key-here" >> .env
```

#### Issue: "No module named 'nltk'"
```bash
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server
source venv/bin/activate
pip install nltk
```

#### Issue: "Port 8000 already in use"
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

#### Issue: "Database locked"
```bash
# Stop the server (Ctrl+C)
# Remove lock file
rm carely.db-lock 2>/dev/null

# Restart
bash run_server.sh
```

### Client Issues

#### Issue: "npm command not found"
```bash
# Install Node.js from https://nodejs.org/
# Or use homebrew:
brew install node
```

#### Issue: "Port 5173 already in use"
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or npm will automatically try next available port (5174, etc.)
```

#### Issue: "Cannot connect to server"
```bash
# Make sure server is running first!
# Check http://localhost:8000/api/v1/health

# If server is on different port, update client config
# Check: client/src/utils/api.ts for API_BASE_URL
```

#### Issue: "Module not found" errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## 🔄 Complete Workflow

### Starting Everything

```bash
# Terminal 1: Server
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server
source venv/bin/activate
bash run_server.sh

# Terminal 2: Client (in a NEW terminal)
cd /Users/arvindrangarajan/PythonLab/Carely-AI/client
npm run dev

# Terminal 3: Testing (optional)
cd /Users/arvindrangarajan/PythonLab/Carely-AI/server
source venv/bin/activate
python test_rag_integration.py
```

### Stopping Everything

```bash
# In each terminal:
Ctrl+C  # Stop the server/client

# Or force kill if needed:
pkill -f "uvicorn app.main:app"
pkill -f "vite"
```

---

## 📊 Checking Status

### Server Status

```bash
# Check if server is running
curl http://localhost:8000/ping
# Should return: {"message":"pong"}

# Check API documentation
open http://localhost:8000/docs

# Check health
curl http://localhost:8000/api/v1/health
```

### Client Status

```bash
# Check if client is running
curl http://localhost:5173
# Should return HTML

# Open in browser
open http://localhost:5173
```

---

## 🌐 URLs Reference

### Server (Backend)
- **Base URL:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health
- **Chat Endpoint:** http://localhost:8000/api/v1/chat

### Client (Frontend)
- **Main App:** http://localhost:5173
- **Login:** http://localhost:5173/auth
- **Chat:** http://localhost:5173/chat

---

## 📝 Available Scripts

### Server Scripts

```bash
# Start server (development mode with auto-reload)
bash run_server.sh

# Run tests
bash run_tests.sh

# Test RAG integration
python test_rag_integration.py

# Check API key loading
python test_openai_key.py
```

### Client Scripts

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

---

## 🎯 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    CARELY-AI QUICK START                     │
├─────────────────────────────────────────────────────────────┤
│ SERVER (Terminal 1):                                         │
│   cd ~/PythonLab/Carely-AI/server                           │
│   bash run_server.sh                                         │
│   → http://localhost:8000                                    │
├─────────────────────────────────────────────────────────────┤
│ CLIENT (Terminal 2):                                         │
│   cd ~/PythonLab/Carely-AI/client                           │
│   npm run dev                                                │
│   → http://localhost:5173                                    │
├─────────────────────────────────────────────────────────────┤
│ STOP:                                                        │
│   Ctrl+C in each terminal                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Environment Variables

### Server `.env` file should contain:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-proj-your-key-here

# Pinecone API Key (optional, for RAG)
PINECONE_API_KEY=your-pinecone-key-here
RAG_ENABLED=true

# Application Settings
SECRET_KEY=your-secret-key-for-jwt
DEBUG=True

# Database
DATABASE_URL=sqlite:///./carely.db

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8080"]
```

---

## ✅ Verification Checklist

Before starting, verify:

- [ ] Server `.env` file exists and has `OPENAI_API_KEY`
- [ ] Server `venv` directory exists
- [ ] Server dependencies installed (`pip list` shows fastapi, uvicorn, etc.)
- [ ] Client `node_modules` directory exists
- [ ] Client dependencies installed (`npm list` shows react, vite, etc.)
- [ ] Port 8000 is free (for server)
- [ ] Port 5173 is free (for client)

---

## 🎉 Success!

When both are running:

1. **Server console** shows: `Application startup complete`
2. **Client console** shows: `ready in xxx ms`
3. **Browser** at http://localhost:5173 shows Carely-AI login page
4. **API Docs** at http://localhost:8000/docs are accessible

---

**Need Help?**
- Check `server/README.md` for server details
- Check `server/QUICK_START.md` for quick setup
- Check `server/TEST_GUIDE.md` for testing
- Check `server/API_KEY_AUDIT.md` for API key configuration

**Happy Coding! 🚀**

