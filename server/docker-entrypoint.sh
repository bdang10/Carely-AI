#!/bin/bash
# Docker entrypoint script for Carely AI backend

set -e

echo "🚀 Starting Carely AI Backend..."

# Wait a moment for database to be ready (if using external Postgres)
echo "⏳ Waiting for database connection..."
sleep 2

# Run Alembic migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Check if migrations succeeded
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "❌ Database migration failed"
    exit 1
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
