from fastapi import APIRouter

from app.api.v1.endpoints import auth, empleados, empresas, nomina

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(empresas.router)
api_router.include_router(empleados.router)
api_router.include_router(nomina.router)
