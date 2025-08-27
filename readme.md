# URL Shortener Service

A FastAPI-based URL shortener service with PostgreSQL and Redis integration, built for Firouzeh Digital Company.

**Note:** Due to time constraints during development, some advanced features may be limited in scope, but the core functionality is fully implemented with a clean, scalable architecture.

## Architecture Overview

This project follows clean architecture principles with clear separation of concerns:

```
├── Domain Layer (models/, interfaces/)
├── Application Layer (services/)
├── Infrastructure Layer (infrastructure/)
├── Presentation Layer (apies/)
└── Cross-cutting Concerns (utils/, configs/)
```

## 📁 Project Structure

```
├── alembic/                          # Database migration files
│   ├── versions/                     # Migration versions
│   ├── env.py                       # Alembic environment configuration
│   └── script.py.mako              # Migration template
├── apies/                           # API endpoints (presentation layer)
│   └── shortener/
│       ├── dto.py                   # Data Transfer Objects
│       └── router.py                # FastAPI route definitions
├── configs/                         # Configuration management
│   └── settings.py                  # Application settings using Pydantic
├── infrastructure/                  # Infrastructure layer
│   ├── cache/
│   │   ├── redis.py                # Redis connection and operations
│   │   └── redis_util.py           # Redis utility functions and caching
│   ├── databases/
│   │   └── postgres.py             # PostgreSQL connection management
│   └── initializer.py              # Infrastructure initialization
├── interfaces/                      # Abstract interfaces/contracts
│   └── generate_shorter_url_interface.py
├── models/                          # Domain models (SQLAlchemy)
│   └── url_shortener.py            # URL shortener entity
├── repository/                      # Data access layer
│   └── url_shortener_repository.py # URL shortener data operations
├── services/                        # Business logic layer
│   └── url_shortener/
│       ├── url_shortener_generator.py        # URL generation logic
│       ├── url_shortener_generator_helper.py # Base62 encoding helpers
│       └── url_shorterner_service.py         # Main business service
├── utils/                           # Utility functions
│   ├── get_connections.py           # Dependency injection for connections
│   └── get_services.py             # Dependency injection for services
├── docker-compose.yml               # Multi-container Docker setup
├── Dockerfile                       # Application containerization
├── requirements.txt                 # Python dependencies
├── alembic.ini                     # Alembic configuration
└── main.py                         # FastAPI application entry point
```

## 🚀 Features

- **URL Shortening**: Convert long URLs to short, Base62-encoded identifiers
- **URL Resolution**: Retrieve original URLs from shortened versions
- **PostgreSQL Integration**: Persistent storage with SQLAlchemy ORM
- **Redis Caching**: High-performance caching layer
- **Database Migrations**: Automated schema management with Alembic
- **Health Checks**: Application and dependency health monitoring
- **Containerized Deployment**: Docker and Docker Compose support
- **Clean Architecture**: Modular, testable, and maintainable code structure

## Technology Stack

- **Framework**: FastAPI 0.116.1
- **Database**: PostgreSQL with AsyncPG driver
- **Caching**: Redis 6.4.0
- **ORM**: SQLAlchemy 2.0.43 (async)
- **Migration**: Alembic 1.16.4
- **Validation**: Pydantic 2.11.7
- **Containerization**: Docker & Docker Compose
- **Python**: 3.12

## Quick Start

### Using Docker (Recommended)

1. **Start the services**
   ```bash
   docker-compose up -d
   ```

2. **Check service health**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Access the API**
   - API Base URL: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - ReDoc Documentation: `http://localhost:8000/redoc`

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start PostgreSQL and Redis**
   ```bash
   docker-compose up -d postgres redis
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🔧 Configuration

The application uses environment-based configuration through `configs/settings.py`:

```python
# Key configuration options
PROJECT_NAME: str = "FastAPI App"
VERSION: str = "0.1.0" 
DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/fastapi_db"
REDIS_URL: str = "redis://localhost:6379/0"
ALLOWED_HOSTS: List[str] = ["*"]
SECRET_KEY: str = "your-secret-key-here"
```

## API Endpoints

### Create Shortened URL
```http
POST /api/generator
Content-Type: application/json

{
  "url": "https://www.example.com/very/long/url/that/needs/shortening"
}
```

**Response:**
```json
{
  "url": "abc123"
}
```

### Resolve Shortened URL
```http
GET /api/generator/{shorted_url}
```

**Response:**
```json
{
  "url": "https://www.example.com/very/long/url/that/needs/shortening"
}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "db": true,
  "redis": true
}
```

## Architecture Details

### Architecture Layers

1. **Domain Layer** (`models/`, `interfaces/`)
   - Core business entities and contracts
   - Framework-independent business rules

2. **Application Layer** (`services/`)
   - Use cases and business logic orchestration
   - Application-specific rules

3. **Infrastructure Layer** (`infrastructure/`)
   - External service integrations (database, cache)
   - Framework-specific implementations

4. **Presentation Layer** (`apies/`)
   - HTTP endpoints and request/response handling
   - Input validation and serialization

### Key Design Patterns

- **Dependency Injection**: Clean separation of concerns
- **Repository Pattern**: Data access abstraction
- **Interface Segregation**: Pluggable algorithm implementations
- **Factory Pattern**: Infrastructure component creation

### URL Shortening Algorithm

The service uses Base62 encoding to generate short, URL-safe identifiers:
- Character set: `0-9A-Za-z` (62 characters)
- Collision-resistant through database auto-increment IDs
- Deterministic and reversible encoding

## Database Schema

```sql
-- URL shorteners table
CREATE TABLE url_shorters (
    id SERIAL PRIMARY KEY,
    original_url VARCHAR(2048) NOT NULL,
    shorted_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX ix_url_shorter_original_url ON url_shorters(original_url);
```


##  License

This project is part of a code challenge for Firouzeh Digital Company.

## Troubleshooting

1. **Database Connection Error**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   ```

2. **Redis Connection Error**
   ```bash
   # Check Redis connectivity
   docker-compose exec redis redis-cli ping
   ```

3. **Migration Issues**
   ```bash
   # Reset and reapply migrations
   alembic downgrade base
   alembic upgrade head
   ```
