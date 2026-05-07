"""Helpers geodésicos: SIRGAS 2000 (EPSG:4674) <-> UTM 23S (EPSG:31983).

Funções puras — sem DB. Usadas pelas APIs de lotes e pelo gerador de memorial.
"""
from __future__ import annotations

import math
from typing import TypedDict

from pyproj import Transformer
from shapely.geometry import Polygon

_to_utm = Transformer.from_crs("EPSG:4674", "EPSG:31983", always_xy=True)
_from_utm = Transformer.from_crs("EPSG:31983", "EPSG:4674", always_xy=True)


class VerticeData(TypedDict):
    marco: str
    e_utm: float
    n_utm: float
    lat: float
    lon: float
    lat_dms: str
    lon_dms: str


class SegmentoData(TypedDict):
    de: str
    para: str
    distancia_m: float
    azimute_dms: str
    azimute_deg: float
    confrontante: str


def lonlat_to_utm(lon: float, lat: float) -> tuple[float, float]:
    return _to_utm.transform(lon, lat)


def utm_to_lonlat(e: float, n: float) -> tuple[float, float]:
    return _from_utm.transform(e, n)


def decimal_to_dms(value: float) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    d = int(v)
    m_float = (v - d) * 60
    m = int(m_float)
    s = (m_float - m) * 60
    return f"{sign}{d}°{m:02d}'{s:05.2f}\""


def vertices_data(coords: list[tuple[float, float]]) -> list[VerticeData]:
    out: list[VerticeData] = []
    for i, (lon, lat) in enumerate(coords):
        e, n = lonlat_to_utm(lon, lat)
        out.append(
            {
                "marco": f"M{i}",
                "e_utm": e,
                "n_utm": n,
                "lat": lat,
                "lon": lon,
                "lat_dms": decimal_to_dms(lat),
                "lon_dms": decimal_to_dms(lon),
            }
        )
    return out


def segmentos(coords: list[tuple[float, float]]) -> list[SegmentoData]:
    n = len(coords)
    out: list[SegmentoData] = []
    for i in range(n):
        a = coords[i]
        b = coords[(i + 1) % n]
        a_utm = lonlat_to_utm(*a)
        b_utm = lonlat_to_utm(*b)
        d_e = b_utm[0] - a_utm[0]
        d_n = b_utm[1] - a_utm[1]
        dist = math.hypot(d_e, d_n)
        az = math.degrees(math.atan2(d_e, d_n))
        if az < 0:
            az += 360
        out.append(
            {
                "de": f"M{i}",
                "para": f"M{(i + 1) % n}",
                "distancia_m": dist,
                "azimute_dms": decimal_to_dms(az),
                "azimute_deg": az,
                "confrontante": "________________",
            }
        )
    return out


def area_perimetro_m(
    coords: list[tuple[float, float]],
) -> tuple[float, float]:
    """Área (m²) via UTM 23S e perímetro (m) somando distâncias UTM."""
    utm = [lonlat_to_utm(lon, lat) for lon, lat in coords]
    poly = Polygon(utm)
    perim = sum(
        math.hypot(
            utm[(i + 1) % len(utm)][0] - utm[i][0],
            utm[(i + 1) % len(utm)][1] - utm[i][1],
        )
        for i in range(len(utm))
    )
    return poly.area, perim
