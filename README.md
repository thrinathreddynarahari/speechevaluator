# English Evaluation Service

An internal FastAPI service for evaluating English communication skills from audio recordings using ElevenLabs Speech-to-Text and Claude AI analysis.

## Features

- Audio transcription via ElevenLabs Speech-to-Text API
- AI-powered evaluation using Claude (Anthropic) via LangChain
- Detailed scoring across multiple dimensions (fluency, grammar, pronunciation, vocabulary, structure)
- Actionable improvement recommendations
- Azure AD authentication via Bearer tokens
- PostgreSQL database with Alembic migrations

## Project Structure

```
english-evaluation-service/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_evaluation_schema.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── __init__.py
│   └── main.py
├── config/
│   ├── __init__.py
│   ├── database.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── employee.py
│   └── evaluation.py
├── repositories/
│   ├── __init__.py
│   └── evaluation_repository.py
├── routers/
│   ├── v1/
│   │   ├── __init__.py
│   │   └── evaluation.py
│   └── __init__.py
├── schemas/
│   ├── __init__.py
│   └── evaluation.py
├── services/
│   ├── __init__.py
│   ├── elevenlabs_service.py
│   └── report_service.py
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python 3.12+
- PostgreSQL database with an existing `public.employee` table
- ElevenLabs API key
- Anthropic API key
- Azure AD application for authentication

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -e .
```

Or install directly:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic pydantic pydantic-settings python-multipart httpx langchain-anthropic langchain-core PyJWT cryptography pytz requests langchain_groq
```

### 3. Configure Environment Variables

Copy the example environment file and update with your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Azure AD Authentication
OPENID_CONFIG_URL=https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
VALID_AUDIENCE=api://your-app-id
VALID_ISSUER=https://sts.windows.net/{tenant-id}/
CLIENT_ID=your-client-id
TENANT_ID=your-tenant-id

# ElevenLabs
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_MODEL_ID=scribe_v1

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
CLAUDE_MODEL=claude-sonnet-4-20250514

# Optional
TIMEZONE=Asia/Kolkata
MAX_UPLOAD_MB=25
```

### 4. Database Migrations

The service uses a separate `evaluation` schema to avoid conflicts with existing tables.

**Important**: The `public.employee` table must already exist in your database.

Run migrations:

```bash
# Apply all migrations
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history
```

### 5. Run the Server

Development mode:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, access the interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health Check

```
GET /health
```

### Generate Evaluation Report

```
POST /api/v1/evaluations/report
```

**Request**: `multipart/form-data`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| file | File | Yes | - | Audio or video file |
| language_code | string | No | "eng" | ISO 639-3 language code |
| diarize | boolean | No | true | Enable speaker diarization |
| tag_audio_events | boolean | No | true | Tag audio events |

**Headers**:
```
Authorization: Bearer <azure-ad-token>
Content-Type: multipart/form-data
```

**Response**: `200 OK`

```json
{
  "evaluation_id": "uuid",
  "report_id": "uuid",
  "transcription": "transcribed text...",
  "report": {
    "overall_score": 75,
    "summary": "Good communication skills...",
    "strengths": ["Clear articulation", "..."],
    "improvements": ["Grammar accuracy", "..."],
    "fluency": {"score": 80, "notes": "..."},
    "grammar": {"score": 65, "notes": "..."},
    "pronunciation": {"score": 78, "notes": "..."},
    "vocabulary": {"score": 82, "notes": "..."},
    "structure": {"score": 70, "notes": "..."},
    "action_plan": [
      {"item": "...", "why": "...", "how": "..."}
    ]
  }
}
```

## Example Usage

### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/evaluations/report" \
  -H "Authorization: Bearer YOUR_AZURE_AD_TOKEN" \
  -F "file=@/path/to/audio.mp3" \
  -F "language_code=eng" \
  -F "diarize=true" \
  -F "tag_audio_events=true"
```

### Python Example

```python
import httpx

url = "http://localhost:8000/api/v1/evaluations/report"
headers = {"Authorization": "Bearer YOUR_AZURE_AD_TOKEN"}

with open("audio.mp3", "rb") as f:
    files = {"file": ("audio.mp3", f, "audio/mpeg")}
    data = {"language_code": "eng", "diarize": "true"}
    response = httpx.post(url, headers=headers, files=files, data=data)

print(response.json())
```

## Error Responses

| Status | Description |
|--------|-------------|
| 401 | Authentication failed |
| 422 | Invalid file or validation error |
| 502 | External service failure (ElevenLabs/Claude) |
| 500 | Internal server error |

## Database Schema

The service creates tables in the `evaluation` schema:

- `evaluation.employee_evaluation` - Stores evaluation records with transcription feedback
- `evaluation.employee_evaluation_reports` - Stores generated evaluation reports (JSONB)
- `evaluation.alembic_version` - Alembic migration tracking

The `public.employee` table is referenced but never modified.

## License

Internal use only.