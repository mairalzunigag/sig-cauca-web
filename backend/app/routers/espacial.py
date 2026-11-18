"""F3 · Consultas espaciales ejecutadas en PostGIS.

Justificación técnica (también en el README):
  * Las geometrías se almacenan en EPSG:4326 (grados). Las distancias y áreas en
    grados no tienen significado métrico, por eso las operaciones métricas se
    hacen sobre el tipo `geography` (cálculo sobre el elipsoide WGS 84, en metros).
  * Los puntos que llegan del mapa (clic de Leaflet) están en lon/lat WGS 84.
  * Relación punto-polígono → ST_Covers (incluye el borde, a diferencia de ST_Contains).
  * Cercanía en metros → ST_DWithin (usa el índice GIST sobre geom::geography)
    y ST_Distance para ordenar.
"""
from fastapi import APIRouter, Query

from ..db import consultar, feature_collection

router = APIRouter(prefix="/espacial", tags=["F3 · Consulta espacial"])

# Rango válido de Colombia continental para validar la entrada
LON = Query(ge=-80, le=-66, description="Longitud WGS 84")
LAT = Query(ge=-5, le=14, description="Latitud WGS 84")


@router.get("/punto")
def que_hay_en_el_punto(lon: float = LON, lat: float = LAT):
    """¿En qué municipio y vereda cae un punto? (ST_Covers punto-polígono)."""
    sql_mun = """
        SELECT cod_municipio, nombre_municipio
        FROM municipio
        WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326))
    """
    sql_ver = """
        SELECT v.id_vereda, v.nombre_vereda, v.cod_municipio,
               m.nombre_municipio AS municipio_declarado,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(v.geom, 0.0001), 6) AS geometria
        FROM vereda v
        JOIN municipio m ON m.cod_municipio = v.cod_municipio
        WHERE ST_Covers(v.geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326))
    """
    p = {"lon": lon, "lat": lat}
    mun = consultar(sql_mun, p)
    ver = consultar(sql_ver, p)
    return {
        "punto": {"lon": lon, "lat": lat},
        "municipio": mun[0] if mun else None,
        "veredas": feature_collection(ver, id_campo="id_vereda"),
        "dentro_del_departamento": bool(mun),
    }


@router.get("/cerca")
def veredas_cercanas(
    lon: float = LON,
    lat: float = LAT,
    radio_m: float = Query(5000, gt=0, le=100000, description="Radio de búsqueda en metros"),
    limite: int = Query(50, ge=1, le=200),
):
    """Veredas a una distancia ≤ radio_m del punto (ST_DWithin + ST_Distance, en metros).

    La distancia a un polígono es 0 si el punto cae dentro de él.
    """
    sql = """
        WITH p AS (
            SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography AS g
        )
        SELECT v.id_vereda, v.nombre_vereda, m.nombre_municipio,
               round(ST_Distance(v.geom::geography, p.g)::numeric, 1) AS distancia_m,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(v.geom, 0.0002), 6) AS geometria
        FROM vereda v
        JOIN municipio m ON m.cod_municipio = v.cod_municipio, p
        WHERE ST_DWithin(v.geom::geography, p.g, %(radio)s)
        ORDER BY distancia_m, v.nombre_vereda
        LIMIT %(limite)s
    """
    filas = consultar(sql, {"lon": lon, "lat": lat, "radio": radio_m, "limite": limite})
    return feature_collection(
        filas, id_campo="id_vereda",
        extra={"centro": {"lon": lon, "lat": lat}, "radio_m": radio_m, "total": len(filas)},
    )
