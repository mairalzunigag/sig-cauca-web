"""Conexión con PostgreSQL/PostGIS mediante Psycopg 3 y utilidades GeoJSON."""
import json
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DB

# Pool de conexiones: se abre al iniciar la API y se cierra al apagarla.
pool = ConnectionPool(
    conninfo=" ".join(f"{k}={v}" for k, v in DB.items() if v != ""),
    min_size=1,
    max_size=5,
    open=False,
    kwargs={"row_factory": dict_row},   # cada fila llega como diccionario
)


@contextmanager
def cursor():
    """Entrega un cursor; hace commit/rollback y devuelve la conexión al pool."""
    with pool.connection() as con:
        with con.cursor() as cur:
            yield cur


def consultar(sql: str, params: dict | tuple | None = None) -> list[dict]:
    """Ejecuta un SELECT PARAMETRIZADO y devuelve todas las filas.

    Los valores del usuario viajan en `params` (%(nombre)s); Psycopg los envía
    separados del texto SQL, por lo que no hay concatenación ni inyección SQL.
    """
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def consultar_uno(sql: str, params: dict | tuple | None = None) -> dict | None:
    filas = consultar(sql, params)
    return filas[0] if filas else None


def feature_collection(filas: list[dict], id_campo: str | None = None,
                       extra: dict | None = None) -> dict:
    """Construye un GeoJSON FeatureCollection a partir de filas SQL.

    Convención: la columna `geometria` contiene ST_AsGeoJSON(...) (texto) y el
    resto de columnas pasan a `properties`.
    """
    features = []
    for fila in filas:
        props = {k: v for k, v in fila.items() if k != "geometria"}
        feat = {
            "type": "Feature",
            "geometry": json.loads(fila["geometria"]) if fila.get("geometria") else None,
            "properties": props,
        }
        if id_campo:
            feat["id"] = fila[id_campo]
        features.append(feat)
    fc = {"type": "FeatureCollection", "features": features}
    if extra:
        fc.update(extra)
    return fc
