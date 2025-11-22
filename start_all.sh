#!/bin/bash
# Carely-AI Application Launcher
# Starts both server and client

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVER_DIR="$SCRIPT_DIR/server"
CLIENT_DIR="$SCRIPT_DIR/client"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Carely-AI Healthcare Assistant Launcher           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if server directory exists
if [ ! -d "$SERVER_DIR" ]; then
    echo -e "${RED}❌ Error: Server directory not found at $SERVER_DIR${NC}"
    exit 1
fi

# Check if client directory exists
if [ ! -d "$CLIENT_DIR" ]; then
    echo -e "${RED}❌ Error: Client directory not found at $CLIENT_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Pre-flight Checks...${NC}"
echo ""

# Check server .env file
if [ ! -f "$SERVER_DIR/.env" ]; then
    echo -e "${RED}❌ Server .env file not found${NC}"
    echo -e "   Create it at: $SERVER_DIR/.env"
    exit 1
else
    echo -e "${GREEN}✓${NC} Server .env file exists"
fi

# Check server venv
if [ ! -d "$SERVER_DIR/venv" ]; then
    echo -e "${RED}❌ Server virtual environment not found${NC}"
    echo -e "   Run: cd $SERVER_DIR && python3 -m venv venv"
    exit 1
else
    echo -e "${GREEN}✓${NC} Server virtual environment exists"
fi

# Check client node_modules
if [ ! -d "$CLIENT_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Client dependencies not installed${NC}"
    echo -e "   Installing now..."
    cd "$CLIENT_DIR"
    npm install
    echo -e "${GREEN}✓${NC} Client dependencies installed"
else
    echo -e "${GREEN}✓${NC} Client dependencies installed"
fi

echo ""
echo -e "${BLUE}🚀 Starting Carely-AI...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null
    
    echo -e "${GREEN}✓${NC} Services stopped"
    echo -e "${BLUE}👋 Goodbye!${NC}"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start server in background
echo -e "${GREEN}[1/2]${NC} Starting Backend Server..."
cd "$SERVER_DIR"
bash run_server.sh > /tmp/carely-server.log 2>&1 &
SERVER_PID=$!
echo -e "      PID: $SERVER_PID"
echo -e "      Log: /tmp/carely-server.log"
echo -e "      URL: ${BLUE}http://localhost:8000${NC}"
echo ""

# Wait a bit for server to start
sleep 3

# Check if server is running
if ! ps -p $SERVER_PID > /dev/null; then
    echo -e "${RED}❌ Server failed to start${NC}"
    echo -e "   Check logs: tail -f /tmp/carely-server.log"
    exit 1
fi

# Start client in background
echo -e "${GREEN}[2/2]${NC} Starting Frontend Client..."
cd "$CLIENT_DIR"
npm run dev > /tmp/carely-client.log 2>&1 &
CLIENT_PID=$!
echo -e "      PID: $CLIENT_PID"
echo -e "      Log: /tmp/carely-client.log"
echo -e "      URL: ${BLUE}http://localhost:5173${NC}"
echo ""

# Wait for client to start
sleep 3

# Check if client is running
if ! ps -p $CLIENT_PID > /dev/null; then
    echo -e "${RED}❌ Client failed to start${NC}"
    echo -e "   Check logs: tail -f /tmp/carely-client.log"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 Success!                             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "  ${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}📝 Logs:${NC}"
echo -e "  Server: tail -f /tmp/carely-server.log"
echo -e "  Client: tail -f /tmp/carely-client.log"
echo ""
echo -e "${YELLOW}🛑 To stop:${NC} Press Ctrl+C"
echo ""
echo -e "${BLUE}Waiting... (Press Ctrl+C to stop all services)${NC}"
echo ""

# Wait for user interrupt
wait

