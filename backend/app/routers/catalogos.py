"""Salud del servicio y catálogos para los filtros del visor."""
from fastapi import APIRouter

from ..db import consultar, consultar_uno

router = APIRouter(tags=["Catálogos y estado"])


@router.get("/salud")
def salud():
    """Comprueba la conexión real con PostgreSQL/PostGIS y cuenta registros."""
    sql = """
        SELECT postgis_version()                         AS postgis,
               current_database()                        AS base_de_datos,
               (SELECT count(*) FROM departamento)       AS departamentos,
               (SELECT count(*) FROM municipio)          AS municipios,
               (SELECT count(*) FROM fuente_limite)      AS fuentes,
               (SELECT count(*) FROM vereda)             AS veredas
    """
    return consultar_uno(sql)


@router.get("/catalogos/fuentes")
def fuentes():
    """Fuentes de los límites veredales con el número de veredas de cada una."""
    sql = """
        SELECT f.id_fuente, f.nombre_fuente, count(v.id_vereda) AS n_veredas
        FROM fuente_limite f
        LEFT JOIN vereda v ON v.id_fuente = f.id_fuente
        GROUP BY f.id_fuente, f.nombre_fuente
        ORDER BY n_veredas DESC
    """
    return consultar(sql)


@router.get("/catalogos/vigencias")
def vigencias():
    sql = """
        SELECT vigencia, count(*) AS n_veredas
        FROM vereda
        GROUP BY vigencia
        ORDER BY vigencia DESC NULLS LAST
    """
    return consultar(sql)
