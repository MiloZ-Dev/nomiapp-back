from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API del SaaS contable de nómina colombiana NomiApp",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["health"])
async def root():
    return {
        "data": {"name": settings.PROJECT_NAME, "version": "1.0.0", "status": "ok"},
        "message": "NomiApp API en línea",
    }


@app.get("/health", tags=["health"])
async def health():
    return {"data": {"status": "healthy"}, "message": "OK"}
