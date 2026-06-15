import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import app.api.routes.auth_routes as auth_endpoints
import app.api.routes.health_routes as health_endpoints
from app.core.config import settings
from app.core.exceptions.http_exceptions import AppException

app = FastAPI(
    title="FastAPI Boilerplate",
    description="Clean architecture FastAPI boilerplate with authentication",
    version="1.0.0",
    contact={
        "name": "FastAPI Boilerplate",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.include_router(health_endpoints.router)
app.include_router(auth_endpoints.router)

# Configure CORS - in production, replace "*" with specific origins
allowed_origins = ["*"] if settings.APP_DEBUG else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, __: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, __: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)  # nosec
