# NomiApp — Backend

SaaS contable multi-empresa para gestión de **nómina colombiana**.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.0 (async) · Alembic · JWT (PyJWT) · bcrypt.

---

## 1. Requisitos

- Python 3.11+
- Docker + Docker Compose (para PostgreSQL y pgAdmin)

## 2. Puesta en marcha

```bash
# 1. Variables de entorno
cp .env.example .env        # (Windows: copy .env.example .env)

# 2. Base de datos + pgAdmin
docker compose up -d
#   PostgreSQL -> localhost:5432  (nomiapp / nomiapp)
#   pgAdmin    -> http://localhost:5050  (admin@nomiapp.co / admin)

# 3. Entorno virtual + dependencias
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 4. Crear tablas + super admin
python -m app.seed

# 5. Levantar la API
uvicorn app.main:app --reload
```

- API:    http://localhost:8000
- Swagger: http://localhost:8000/docs

## 3. Credenciales iniciales (seed)

```
email:    admin@nomiapp.co
password: Admin2025*
```

## 4. Autenticación

1. `POST /api/v1/auth/login` con `{"email", "password"}` → `access_token` (30 min) + `refresh_token` (7 días).
2. Enviar `Authorization: Bearer <access_token>` en los endpoints protegidos.
3. `POST /api/v1/auth/refresh` con `{"refresh_token"}` para renovar.

## 5. Endpoints principales

| Recurso   | Método | Ruta |
|-----------|--------|------|
| Auth      | POST   | `/api/v1/auth/login` |
| Auth      | POST   | `/api/v1/auth/refresh` |
| Auth      | GET    | `/api/v1/auth/me` |
| Empresas  | GET/POST | `/api/v1/empresas/` |
| Empresas  | GET/PUT/DELETE | `/api/v1/empresas/{id}` |
| Empleados | GET/POST | `/api/v1/empresas/{empresa_id}/empleados/` |
| Empleados | GET/PUT  | `/api/v1/empresas/{empresa_id}/empleados/{id}` |
| Contrato  | POST   | `/api/v1/empresas/{empresa_id}/empleados/{id}/contrato` |
| Nómina    | POST   | `/api/v1/empresas/{empresa_id}/nomina/generar` |
| Nómina    | GET    | `/api/v1/empresas/{empresa_id}/nomina/` |
| Nómina    | GET    | `/api/v1/empresas/{empresa_id}/nomina/{id}` |
| Nómina    | POST   | `/api/v1/empresas/{empresa_id}/nomina/{id}/cerrar` |

Todas las respuestas tienen la forma `{"data": ..., "message": "..."}`.

## 6. Lógica de nómina (2026)

- **SMMLV:** $1.750.905 · **Auxilio de transporte:** $249.095 (si salario ≤ 2 SMMLV).
- Salud empleado = 4 % · Pensión empleado = 4 %.
- `total_devengado = salario_base + auxilio_transporte + valor_horas_extra`
- `neto_pagado = total_devengado − (salud + pensión)`

## 7. Migraciones (Alembic)

`python -m app.seed` ya crea las tablas para desarrollo. Para gestionar cambios de esquema en producción:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```
