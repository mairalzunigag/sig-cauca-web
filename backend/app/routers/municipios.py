"""F1 (visualización) y F2 (consulta de atributos) sobre municipios."""
from fastapi import APIRouter, HTTPException, Path, Query

from ..db import consultar, consultar_uno, feature_collection

router = APIRouter(tags=["F1/F2 · Municipios"])


@router.get("/departamento")
def departamento():
    """F1 · Contorno del departamento (tabla departamento, MultiPolygon 4326)."""
    sql = """
        SELECT cod_departamento, nombre_departamento, area_oficial_km2,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.001), 6) AS geometria
        FROM departamento
    """
    return feature_collection(consultar(sql), id_campo="cod_departamento")


@router.get("/municipios")
def municipios(
    simplificar: float = Query(0.0005, ge=0, le=0.05,
                               description="Tolerancia de simplificación en grados (≈55 m por 0.0005)"),
):
    """F1 · Capa de los 42 municipios como GeoJSON FeatureCollection.

    El número de veredas sale de un JOIN con la tabla vereda (relación 1:N).
    """
    sql = """
        SELECT m.cod_municipio,
               m.nombre_municipio,
               m.altitud_msnm,
               count(v.id_vereda)                                AS n_veredas,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geom, %(tol)s), 6) AS geometria
        FROM municipio m
        LEFT JOIN vereda v ON v.cod_municipio = m.cod_municipio
        GROUP BY m.cod_municipio, m.nombre_municipio, m.altitud_msnm, m.geom
        ORDER BY m.cod_municipio
    """
    return feature_collection(consultar(sql, {"tol": simplificar}), id_campo="cod_municipio")


@router.get("/municipios/{cod_municipio}")
def detalle_municipio(
    cod_municipio: str = Path(pattern=r"^\d{5}$", description="Código DIVIPOLA, ej. 19001"),
):
    """F2 · Atributos del municipio + área y perímetro geodésicos calculados en PostGIS.

    ST_Area / ST_Perimeter sobre ::geography devuelven m² y m sobre el elipsoide
    WGS 84 (la geometría se guarda en grados, EPSG:4326, donde ST_Area daría grados²).
    """
    sql = """
        SELECT m.cod_municipio,
               m.nombre_municipio,
               d.nombre_departamento,
               m.altitud_msnm,
               m.norma_creacion,
               m.area_oficial_km2,
               round((ST_Area(m.geom::geography) / 1000000.0)::numeric, 3)      AS area_geodesica_km2,
               round((ST_Perimeter(m.geom::geography) / 1000.0)::numeric, 3)    AS perimetro_km,
               (SELECT count(*) FROM vereda v WHERE v.cod_municipio = m.cod_municipio) AS n_veredas
        FROM municipio m
        JOIN departamento d ON d.cod_departamento = m.cod_departamento
        WHERE m.cod_municipio = %(cod)s
    """
    fila = consultar_uno(sql, {"cod": cod_municipio})
    if not fila:
        raise HTTPException(404, f"Municipio {cod_municipio} no encontrado")

    # Veredas del municipio por fuente de información (JOIN con fuente_limite)
    sql_fuentes = """
        SELECT f.nombre_fuente, count(*) AS n_veredas
        FROM vereda v
        JOIN fuente_limite f ON f.id_fuente = v.id_fuente
        WHERE v.cod_municipio = %(cod)s
        GROUP BY f.nombre_fuente
        ORDER BY n_veredas DESC
    """
    fila["veredas_por_fuente"] = consultar(sql_fuentes, {"cod": cod_municipio})
    return fila
