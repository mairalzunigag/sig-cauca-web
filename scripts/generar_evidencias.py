"""
Genera evidencias técnicas reproducibles en docs/evidencias/:
  * Llama a la API (HTTP) y guarda las respuestas JSON/GeoJSON.
  * Ejecuta, de forma INDEPENDIENTE, consultas SQL directamente en PostgreSQL
    (con otra formulación que la de la API) y compara ambos resultados.
  * Escribe docs/evidencias/verificacion.md con el resultado de cada comparación.

Requisitos: la API debe estar corriendo (uvicorn) y el .env configurado.
    python scripts/generar_evidencias.py [--api http://127.0.0.1:8000]
"""
import argparse
import json
import os
import platform
import time
from datetime import datetime
from pathlib import Path

import psycopg
import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")
OUT = RAIZ / "docs" / "evidencias"
(OUT / "api").mkdir(parents=True, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--api", default="http://127.0.0.1:8000")
API = ap.parse_args().api.rstrip("/")

con = psycopg.connect(host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
                      dbname=os.getenv("PGDATABASE", "sig_cauca"), user=os.getenv("PGUSER", "postgres"),
                      password=os.getenv("PGPASSWORD", ""))


def sql(q, p=None):
    with con.cursor() as cur:
        cur.execute(q, p)
        return cur.fetchall()


def get(ruta, nombre):
    t0 = time.perf_counter()
    r = requests.get(API + ruta, timeout=60)
    ms = round((time.perf_counter() - t0) * 1000)
    r.raise_for_status()
    datos = r.json()
    # Para que el archivo sea legible, las geometrías se resumen (tipo + nº de vértices)
    (OUT / "api" / f"{nombre}.json").write_text(
        json.dumps(resumir(datos), ensure_ascii=False, indent=2), encoding="utf-8")
    return datos, r.status_code, ms, r.headers.get("content-type", "")


def n_vertices(c):
    return 1 if isinstance(c[0], (int, float)) else sum(n_vertices(x) for x in c)


def resumir(o):
    if isinstance(o, dict):
        if "coordinates" in o and "type" in o:
            return {"type": o["type"], "n_vertices": n_vertices(o["coordinates"])}
        return {k: resumir(v) for k, v in o.items()}
    if isinstance(o, list):
        return [resumir(x) for x in o[:60]] + ([f"... ({len(o)-60} más)"] if len(o) > 60 else [])
    return o


filas = []   # (prueba, ruta, http, ms, valor_api, valor_sql, ok)


def comparar(prueba, ruta, nombre, extraer, q, p=None, tol=0):
    datos, http, ms, ctype = get(ruta, nombre)
    va = extraer(datos)
    vs = q(p) if callable(q) else sql(q, p)[0][0]   # consulta SQL directa (valor escalar)
    ok = abs(va - vs) <= tol if isinstance(va, (int, float)) and isinstance(vs, (int, float)) else va == vs
    filas.append((prueba, ruta, f"{http} {ctype.split(';')[0]}", ms, va, vs, ok))


# 1. Estado y conteos
d, *_ = get("/salud", "salud")
comparar("Municipios en /salud", "/salud", "salud", lambda d: d["municipios"],
         "SELECT count(*) FROM municipio")
comparar("Veredas en /salud", "/salud", "salud", lambda d: d["veredas"], "SELECT count(*) FROM vereda")

# 2. F1: capa de municipios
comparar("F1 · nº de municipios (FeatureCollection)", "/municipios", "f1_municipios",
         lambda d: len(d["features"]), "SELECT count(*) FROM municipio")
comparar("F1 · Σ n_veredas de los features", "/municipios", "f1_municipios",
         lambda d: sum(f["properties"]["n_veredas"] for f in d["features"]), "SELECT count(*) FROM vereda")

# 3. F2: detalle (área geodésica) y búsqueda
comparar("F2 · área geodésica Popayán (km²)", "/municipios/19001", "f2_municipio_19001",
         lambda d: float(d["area_geodesica_km2"]),
         lambda _: float(sql("SELECT ST_Area(geom::geography)/1e6 FROM municipio WHERE cod_municipio='19001'")[0][0]),
         tol=0.001)
comparar("F2 · búsqueda 'el cane' (ids)", "/veredas/buscar?q=el%20cane", "f2_buscar",
         lambda d: sorted(x["id_vereda"] for x in d),
         lambda _: sorted(r[0] for r in sql(
             "SELECT id_vereda FROM vereda WHERE translate(lower(nombre_vereda),'áéíóú','aeiou') LIKE %s",
             ("%el cane%",))))

# 4. F3: consulta espacial (formulación independiente: ST_Distance <= radio)
comparar("F3 · veredas ≤ 3 km del punto (ids)", "/espacial/cerca?lon=-76.606&lat=2.444&radio_m=3000&limite=200",
         "f3_cerca", lambda d: sorted(f["id"] for f in d["features"]),
         lambda _: sorted(r[0] for r in sql(
             """SELECT id_vereda FROM vereda WHERE ST_Distance(geom::geography,
                ST_SetSRID(ST_MakePoint(-76.606, 2.444), 4326)::geography) <= 3000""")))
comparar("F3 · municipio que contiene el punto", "/espacial/punto?lon=-76.606&lat=2.444", "f3_punto",
         lambda d: d["municipio"]["cod_municipio"],
         lambda _: sql("""SELECT cod_municipio FROM municipio WHERE ST_Contains(geom,
                 ST_SetSRID(ST_MakePoint(-76.606, 2.444), 4326))""")[0][0])

# 5. F4: filtro combinado y calidad
comparar("F4 · veredas Timbío 100–500 ha", "/veredas?municipio=19807&area_min_ha=100&area_max_ha=500",
         "f4_filtro", lambda d: d["resumen"]["total"],
         """SELECT count(*) FROM vereda WHERE cod_municipio='19807'
            AND ST_Area(geom::geography)/10000 BETWEEN 100 AND 500""")
comparar("F4 · veredas fuera de su municipio", "/calidad/inconsistencias", "f4_calidad",
         lambda d: d["total"],
         """SELECT count(*) FROM vereda v WHERE NOT EXISTS (SELECT 1 FROM municipio m
            WHERE m.cod_municipio=v.cod_municipio AND ST_Covers(m.geom, ST_PointOnSurface(v.geom)))""")

# ---- Informe -----------------------------------------------------------------
ver = sql("SELECT version(), postgis_version()")[0]
md = [f"# Verificación API ↔ PostgreSQL/PostGIS\n",
      f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
      f"- Python {platform.python_version()} · {platform.system()}",
      f"- {ver[0].split(',')[0]} · PostGIS {ver[1].split()[0]}",
      f"- API: {API}\n",
      "| # | Prueba | Endpoint | HTTP | ms | Resultado API | Resultado SQL directo | ¿Coincide? |",
      "|---|--------|----------|------|----|---------------|-----------------------|-----------|"]
for i, (pr, ru, ht, ms, va, vs, ok) in enumerate(filas, 1):
    f = lambda x: (str(x) if len(str(x)) < 40 else str(x)[:37] + "...").replace("|", "\\|")
    md.append(f"| {i} | {pr} | `{ru[:50]}` | {ht} | {ms} | {f(va)} | {f(vs)} | {'✅' if ok else '❌'} |")
todo = all(r[-1] for r in filas)
md.append(f"\n**Resultado global: {'todas las comparaciones coinciden' if todo else 'HAY DIFERENCIAS'}**\n")
md.append("Las respuestas completas (con geometrías resumidas) están en `docs/evidencias/api/`.")
(OUT / "verificacion.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
raise SystemExit(0 if todo else 1)
