"""SIG Web del Cauca - API REST (FastAPI) sobre PostgreSQL/PostGIS.

Ejecutar desde la raíz del repositorio:
    uvicorn backend.app.main:app --reload
Documentación interactiva (Swagger): http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import FRONTEND_DIR
from .routers import calidad, catalogos, espacial, municipios, veredas


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.pool.open(wait=True, timeout=10)   # falla pronto si PostgreSQL no responde
    yield
    db.pool.close()


app = FastAPI(
    title="SIG Web del Cauca",
    description="API sobre una geodatabase PostgreSQL/PostGIS: departamento, "
                "municipios, veredas y fuentes de los límites veredales.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: permite abrir el frontend desde otro servidor (p. ej. http.server :5500).
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"],
                   allow_headers=["*"])

app.include_router(catalogos.router)
app.include_router(municipios.router)
app.include_router(veredas.router)
app.include_router(espacial.router)
app.include_router(calidad.router)

# El frontend estático también se sirve desde la API (una sola orden para ejecutar).
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND_DIR / "index.html")
