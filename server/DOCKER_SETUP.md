# Docker Setup for Carely AI Backend

This guide explains how to run the Carely AI backend using Docker with Neon serverless Postgres.

## Prerequisites

- Docker and Docker Compose installed
- Neon Postgres database created with connection string
- `.env` file configured with your Neon credentials

## Quick Start

1. **Set up your environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your Neon connection string:**
   ```bash
   DATABASE_URL=postgresql://username:password@ep-xxxxx-pooler.region.aws.neon.tech/carely?sslmode=require
   OPENAI_API_KEY=sk-proj-your-key-here
   ```

3. **Build and start the container:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

## What Happens on Startup

The Docker container automatically:

1. ✅ Installs all Python dependencies (including `psycopg2-binary`)
2. ✅ Waits for database connection
3. ✅ Runs Alembic migrations (`alembic upgrade head`)
4. ✅ Starts the FastAPI server with hot-reload enabled

## Docker Commands

### Start the Application

**First time (build and start):**
```bash
docker-compose up --build
```

**Subsequent starts:**
```bash
docker-compose up
```

**Run in background (detached mode):**
```bash
docker-compose up -d
```

### Stop the Application

**Stop containers:**
```bash
docker-compose down
```

**Stop and remove volumes (clean slate):**
```bash
docker-compose down -v
```

### View Logs

**Follow logs in real-time:**
```bash
docker-compose logs -f
```

**View last 100 lines:**
```bash
docker-compose logs --tail=100
```

### Rebuild Container

**After dependency changes (requirements.txt):**
```bash
docker-compose up --build --force-recreate
```

**Force rebuild from scratch:**
```bash
docker-compose build --no-cache
docker-compose up
```

## Running Alembic Migrations in Docker

### Method 1: Automatic (Recommended)

Migrations run automatically when the container starts via the entrypoint script.

### Method 2: Manual

**Access the container shell:**
```bash
docker exec -it carely-api bash
```

**Inside the container, run Alembic commands:**
```bash
# Check current migration
alembic current

# View migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "Add new field to User model"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

**Exit the container:**
```bash
exit
```

## Development Workflow

### Code Changes

The following directories are mounted as volumes for hot-reload:
- `./app` → `/app/app` (application code)
- `./alembic` → `/app/alembic` (migrations)
- `./RAG` → `/app/RAG` (RAG files)

Changes to these files will automatically reload the server.

### Adding New Dependencies

1. Add the package to `requirements.txt`
2. Rebuild the container:
   ```bash
   docker-compose up --build --force-recreate
   ```

### Creating New Migrations

**Option 1: Inside the container**
```bash
docker exec -it carely-api alembic revision --autogenerate -m "Description"
docker exec -it carely-api alembic upgrade head
```

**Option 2: Interactive shell**
```bash
docker exec -it carely-api bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
exit
```

## Troubleshooting

### Container won't start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**
- Missing `.env` file → Copy from `.env.example`
- Invalid DATABASE_URL → Check Neon connection string
- Missing OPENAI_API_KEY → Add to `.env`

### Database connection errors

**"could not connect to server":**
- Verify DATABASE_URL in `.env` is correct
- Check that you're using the **pooled** connection string from Neon
- Ensure `sslmode=require` is in the connection string
- Verify Neon database is not suspended

**"relation does not exist":**
- Migrations may not have run
- Check logs: `docker-compose logs | grep alembic`
- Manually run migrations: `docker exec -it carely-api alembic upgrade head`

### Migration errors

**"Target database is not up to date":**
```bash
docker exec -it carely-api alembic upgrade head
```

**"Can't locate revision identified by...":**
```bash
docker exec -it carely-api alembic history
docker exec -it carely-api alembic current
```

### Hot-reload not working

**Restart the container:**
```bash
docker-compose restart
```

**Or rebuild:**
```bash
docker-compose up --build
```

### Clean slate (reset everything)

**Remove containers, volumes, and rebuild:**
```bash
docker-compose down -v
docker-compose up --build --force-recreate
```

## Docker Container Structure

```
/app
├── alembic/           # Database migrations
├── alembic.ini        # Alembic config
├── app/               # Application code
│   ├── agents/        # AI agents
│   ├── api/           # API endpoints
│   ├── core/          # Config & security
│   ├── db/            # Database
│   ├── models/        # SQLAlchemy models
│   └── schemas/       # Pydantic schemas
├── RAG/               # RAG implementation
└── docker-entrypoint.sh  # Startup script
```

## Environment Variables

All environment variables are loaded from `.env`:

**Required:**
- `DATABASE_URL` - Neon Postgres connection string (pooled)
- `OPENAI_API_KEY` - OpenAI API key
- `SECRET_KEY` - JWT secret key

**Optional:**
- `PINECONE_API_KEY` - For RAG functionality
- `RAG_ENABLED` - Enable/disable RAG (true/false)
- `DEBUG` - Debug mode (True/False)
- `BACKEND_CORS_ORIGINS` - CORS allowed origins

## Performance Tips

1. **Use pooled connection string:** Neon provides both pooled and unpooled URLs. Always use the **pooled** URL for the application.

2. **Connection pooling is configured** in `app/db/session.py`:
   - `pool_size=10` - Keep 10 connections in pool
   - `max_overflow=20` - Allow up to 20 additional connections
   - `pool_pre_ping=True` - Verify connections before use
   - `pool_recycle=3600` - Recycle connections after 1 hour

3. **Docker caching:** The Dockerfile is optimized for layer caching. Dependencies are installed before copying code.

## Production Considerations

For production deployment:

1. **Remove volume mounts** from `docker-compose.yml` (no hot-reload needed)
2. **Set DEBUG=False** in environment
3. **Use stronger SECRET_KEY**
4. **Consider using Docker secrets** for sensitive data
5. **Add health checks** to docker-compose.yml
6. **Use multi-stage builds** for smaller image size
7. **Run as non-root user** in production

## Additional Resources

- [Neon Documentation](https://neon.tech/docs)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
