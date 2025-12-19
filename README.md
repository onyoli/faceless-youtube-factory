# Faceless YouTube Factory

AI-powered video generation and YouTube upload automation. Create engaging videos from text prompts with AI-generated scripts, text-to-speech voices, and automated publishing.

## Features

- **AI Script Generation** - Groq's LLama 3.3 generates multi-speaker video scripts
- **Intelligent Voice Casting** - AI selects from 100+ Microsoft Edge TTS voices
- **Voice Customization** - Adjust pitch and speed per character
- **Video Composition** - Auto-generated videos with subtitles
- **YouTube Integration** - One-click upload with AI-generated metadata
- **Real-time Updates** - WebSocket notifications for generation progress

## Architecture

This project uses a **containerized client-server architecture** with three tiers:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│   PostgreSQL    │
│   (Next.js)     │◀────│   (FastAPI)     │◀────│    Database     │
│   Port 3000     │ WS  │   Port 8000     │     │   Port 5432     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

The backend uses **LangGraph** to orchestrate an event-driven video generation pipeline:

```
Script Writer → Casting Director → Audio Generator → Video Composer → YouTube Uploader
```

## Tech Stack

**Backend:** FastAPI, LangGraph, Groq LLM, Edge-TTS, MoviePy, PostgreSQL, SQLAlchemy

**Frontend:** Next.js 15, TypeScript, shadcn/ui, TanStack Query, Tailwind CSS

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Groq API key ([console.groq.com](https://console.groq.com/keys))
- Google Cloud project with YouTube Data API v3 enabled

### Setup

```bash
# Clone and configure
git clone https://github.com/yourusername/faceless-youtube-factory.git
cd faceless-youtube-factory
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up --build
```

Access the app at http://localhost:3000

### Development

For hot-reloading:

```bash
docker-compose watch
```

Or run services separately:

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend  
cd frontend && npm install && npm run dev
```

## Configuration

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for OAuth tokens |
| `DATABASE_URL` | PostgreSQL connection string |

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects` | Create video project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Get project details |
| PUT | `/api/v1/projects/{id}/cast` | Update voice assignments |
| GET | `/api/v1/voices` | List available voices |
| POST | `/api/v1/youtube/projects/{id}/upload-to-youtube` | Upload to YouTube |

Full API docs available at http://localhost:8000/docs

## License

MIT
