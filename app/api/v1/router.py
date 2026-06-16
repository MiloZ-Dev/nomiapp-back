from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, employees, payroll, payroll_auto

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(employees.router)
api_router.include_router(payroll.router)
api_router.include_router(payroll_auto.router)
