"""
Carga los shapefiles de data/raw/ en las 4 tablas de la geodatabase PostGIS.

Uso (con el entorno virtual activo y el archivo .env configurado):
    python scripts/cargar_datos.py

Pasos:
  1. Lee cada shapefile con pyogrio (geometrías en WKB + atributos).
  2. Reproyecta a EPSG:4326 DENTRO de PostGIS con ST_Transform
     (departamento y municipio vienen en EPSG:9377 MAGNA-SIRGAS Origen Nacional;
      veredas ya viene en EPSG:4326).
  3. Repara geometrías inválidas (ST_MakeValid) y las convierte a MultiPolygon.
  4. Inserta con consultas parametrizadas (sin concatenar valores en el SQL).

Ejecuta primero sql/01_esquema.sql (o usa --crear-esquema).
"""
import argparse
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pyogrio.raw import read as read_raw

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"

load_dotenv(RAIZ / ".env")


def conexion():
    return psycopg.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "sig_cauca"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


def leer(nombre):
    """Devuelve (srid, lista de dicts con 'wkb' y los atributos)."""
    meta, _fids, geoms, valores = read_raw(str(RAW / f"{nombre}.shp"))
    srid = int(re.search(r"(\d+)$", meta["crs"]).group(1))
    campos = list(meta["fields"])
    filas = []
    for i, g in enumerate(geoms):
        fila = {c: valores[j][i] for j, c in enumerate(campos)}
        fila["wkb"] = bytes(g)
        filas.append(fila)
    return srid, filas


# EPSG:9377 (MAGNA-SIRGAS 2018 / Origen-Nacional) no viene en todas las versiones
# de spatial_ref_sys de PostGIS; se entrega su definición PROJ directamente.
# GRS80 + Transversa de Mercator (lat0=4, lon0=-73, k=0.9992, E0=5 000 000, N0=2 000 000).
PROJ_9377 = ("+proj=tmerc +lat_0=4 +lon_0=-73 +k=0.9992 "
             "+x_0=5000000 +y_0=2000000 +ellps=GRS80 +units=m +no_defs")

# Expresión SQL que deja la geometría lista: EPSG:4326, válida y MultiPolygon.
# %(proj)s es la cadena PROJ de origen (ST_Transform(geom, proj_origen, srid_destino)).
GEOM_SQL = (
    "ST_Multi(ST_CollectionExtract("
    "ST_MakeValid(ST_Transform(ST_GeomFromWKB(%(wkb)s), %(proj)s, 4326)), 3))"
)


def proj_de(srid):
    return PROJ_9377 if srid == 9377 else "+proj=longlat +datum=WGS84 +no_defs"


def limpio(v):
    """Normaliza nulos de la fuente ('NULL', '<Null>', vacío) a None."""
    if v is None:
        return None
    v = str(v).strip()
    return None if v.upper() in ("", "NULL", "<NULL>", "NONE") else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crear-esquema", action="store_true",
                    help="ejecuta antes sql/01_esquema.sql (BORRA y recrea las tablas)")
    args = ap.parse_args()

    with conexion() as con, con.cursor() as cur:
        if args.crear_esquema:
            cur.execute((RAIZ / "sql" / "01_esquema.sql").read_text(encoding="utf-8"))
            print("Esquema creado.")

        # ---- departamento ------------------------------------------------
        srid, filas = leer("CAUCA")
        for f in filas:
            cur.execute(
                f"""INSERT INTO departamento
                      (cod_departamento, nombre_departamento, area_oficial_km2, norma, geom)
                    VALUES (%(cod)s, %(nom)s, %(area)s, %(norma)s, {GEOM_SQL})""",
                {"cod": f["DeCodigo"], "nom": f["DeNombre"], "area": f["DeArea"],
                 "norma": limpio(f["DeNorma"]), "wkb": f["wkb"], "proj": proj_de(srid)},
            )
        print(f"departamento: {len(filas)}")

        # ---- municipio ---------------------------------------------------
        srid, filas = leer("MUNICIPIOS")
        for f in filas:
            cur.execute(
                f"""INSERT INTO municipio
                      (cod_municipio, nombre_municipio, cod_departamento,
                       area_oficial_km2, altitud_msnm, norma_creacion, geom)
                    VALUES (%(cod)s, %(nom)s, left(%(cod)s::varchar, 2), %(area)s, %(alt)s,
                            %(norma)s, {GEOM_SQL})""",
                {"cod": f["MpCodigo"], "nom": f["MpNombre"].strip(),
                 "area": f["MpArea"], "alt": int(f["MpAltitud"]),
                 "norma": limpio(f["MpNorma"]), "wkb": f["wkb"], "proj": proj_de(srid)},
            )
        print(f"municipio: {len(filas)}")

        # ---- fuente_limite (catálogo construido con los valores reales) --
        srid, filas = leer("VEREDAS")
        fuentes = sorted({limpio(f["FUENTE"]) for f in filas if limpio(f["FUENTE"])})
        ids = {}
        for nombre in fuentes:
            cur.execute(
                "INSERT INTO fuente_limite (nombre_fuente) VALUES (%s) RETURNING id_fuente",
                (nombre,),
            )
            ids[nombre] = cur.fetchone()[0]
        print(f"fuente_limite: {len(fuentes)}")

        # ---- vereda ------------------------------------------------------
        for f in filas:
            desc = limpio(f["DESCRIPCIO"])
            cur.execute(
                f"""INSERT INTO vereda
                      (codigo_ver, nombre_vereda, cod_municipio, id_fuente, vigencia,
                       tiene_centro_poblado, observacion, area_ha_fuente, geom)
                    VALUES (%(cv)s, %(nom)s, %(mun)s, %(fte)s, %(vig)s,
                            %(cp)s, %(obs)s, %(area)s, {GEOM_SQL})""",
                {"cv": f["CODIGO_VER"], "nom": f["NOMBRE_VER"].strip(),
                 "mun": f["DPTOMPIO"], "fte": ids[limpio(f["FUENTE"])],
                 "vig": limpio(f["VIGENCIA"]),
                 "cp": desc == "CON CENTRO POBLADO",
                 # cualquier otra descripción es una observación de edición
                 "obs": None if desc in (None, "CON CENTRO POBLADO") else desc,
                 "area": f["AREA_HA"], "wkb": f["wkb"], "proj": proj_de(srid)},
            )
        print(f"vereda: {len(filas)}")

        cur.execute("ANALYZE")
        con.commit()
    print("Carga completa.")


if __name__ == "__main__":
    sys.exit(main())
