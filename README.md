# 🚀 FastAPI Boilerplate - Clean Architecture

> A production-ready FastAPI boilerplate with clean architecture, JWT authentication, and PostgreSQL/SQLite support.

## ✨ Features

- 🏗️ **Clean Architecture** - Layered structure (API/Services/Repositories/Models)
- 🔐 **JWT Authentication** - Complete auth system with refresh tokens
- 🗄️ **Database Support** - PostgreSQL for production, SQLite for testing
- 🔄 **Alembic Migrations** - Database schema versioning
- 🧪 **Testing Suite** - Pytest with fixtures and mocks
- 🐳 **Docker Ready** - Dockerfile included
- 📝 **API Documentation** - Auto-generated with Swagger UI
- ⚙️ **Configuration Management** - Pydantic Settings for env variables
- 🔒 **Security Best Practices** - Password hashing, CORS, JWT validation

## 📂 Project Structure

```
fastapi-boilerplate/
├──.github
|   └── workflows            # workflow on github
|       ├── ci.yml
|       └── security.yml
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── core/                # Configuration & security
│   ├── db/
│   │   └── models/          # SQLAlchemy models
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic
│   └── schemas/             # Pydantic models (DTOs)
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── .env.example             # Environment variables template
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Manager containers
├── pyproject.toml           # Python dependencies
└── .gitignore               # ignored files on git
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or use SQLite for local dev)
- poetry

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Alwil17/fastapi-boilerplate.git
   cd fastapi-boilerplate
   ```


2. **(Recomendado) Configure o Poetry para criar a virtualenv dentro do projeto**

   Este projeto utiliza o Poetry para criar ambiente virtual e gerenciar as dependências. Execute o comando para que o ambiente virtual seja criado dentro do projeto, por padrão.

   ```bash
   poetry config virtualenvs.in-project true
   ```

4. **Instalação de Dependências 📦**

   ### Instalar apenas dependências de produção

   Ao executar "poetry install", automaticamente um ambiente virtual é criado.

   ```bash
   poetry install --no-root --only main
   ```
   Isso instala apenas as dependências essenciais para rodar a aplicação em produção.

   ### Instalar dependências de desenvolvimento (recomendado para desenvolvimento e CI)

   ```bash
   poetry install --with dev --no-root
   ```
   Isso instala todas as dependências, incluindo ferramentas de teste, análise de código, segurança e pre-commit.

   > ⚠️ Caso o comando `poetry install` retorne erro "No such file or directory: 'python'", crie um link simbólico para que `python` aponte para `python3`:
   ```bash
   sudo ln -s $(which python3) /usr/local/bin/python
     ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```
7. **Access the API**
   - API:  http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t fastapi-boilerplate .

# Run the container
docker run -p 8000:8000 --env-file .env fastapi-boilerplate
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

## 🔄 Pre-commit vs CI (GitHub Actions)

Este projeto utiliza tanto hooks locais de pre-commit quanto workflows de CI no GitHub:

- **pre-commit**: Executa verificações de qualidade (black, isort, ruff, mypy, bandit, etc.) automaticamente antes de cada commit local, conforme definido em `.pre-commit-config.yaml`. Isso previne que código fora do padrão seja enviado ao repositório.
- **GitHub Actions (CI/CD)**: Os arquivos `.github/workflows/ci.yml` e `.github/workflows/security.yml` executam as mesmas ferramentas em cada push/pull request no repositório remoto, garantindo que todo código enviado para branches principais também passe pelas checagens.

Assim, a qualidade do código é garantida tanto localmente (antes do commit) quanto remotamente (antes de merge/deploy).

## 📖 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login (get JWT tokens)
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info

### Health Check
- `GET /health` - API health status
- `GET /` - Welcome message

## 🔧 Configuration

Key environment variables (see `.env.example`):

```env
# Application
APP_NAME="FastAPI Boilerplate"
APP_ENV=development
APP_SECRET_KEY=your-secret-key

# Database
DB_ENGINE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=user
DB_PASSWORD=password

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 🏗️ Architecture Principles

This boilerplate follows:

- **Clean Architecture** - Separation of concerns
- **Repository Pattern** - Abstract data access
- **Dependency Injection** - Loose coupling
- **SOLID Principles** - Maintainable code
- **DTOs with Pydantic** - Type safety and validation

## 📚 Tech Stack

- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Authentication
- **Pytest** - Testing framework
- **PostgreSQL** - Production database
- **SQLite** - Testing database

## 🙏 Acknowledgments

- Inspired by clean architecture principles
- Built with FastAPI best practices
- Community-driven development

---

**Made with ❤️ by [Alwil17](https://github.com/Alwil17)**
```
