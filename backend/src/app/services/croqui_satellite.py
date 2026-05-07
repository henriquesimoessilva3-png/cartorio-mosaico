"""Croqui com fundo de satélite — busca tiles Esri, faz stitch + overlay polígono.

Best-effort: se a rede falhar ou Esri retornar tile vazio, devolve None
(o gerador de PDF cai no croqui SVG abstrato).
"""
from __future__ import annotations

import math
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

ESRI_TILE = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
TILE_SIZE = 256
MAX_TILES = 25  # limite de tiles por chamada (~1.5MB no fio)
MAX_ZOOM_ESRI = 19


def _lon2tile_x(lon: float, z: int) -> float:
    return (lon + 180.0) / 360.0 * (2**z)


def _lat2tile_y(lat: float, z: int) -> float:
    rad = math.radians(lat)
    return (
        (1.0 - math.log(math.tan(rad) + 1.0 / math.cos(rad)) / math.pi) / 2.0 * (2**z)
    )


def _pick_zoom(min_lon: float, max_lon: float, min_lat: float, max_lat: float) -> int:
    for z in range(MAX_ZOOM_ESRI, 11, -1):
        x_min = _lon2tile_x(min_lon, z)
        x_max = _lon2tile_x(max_lon, z)
        y_min = _lat2tile_y(max_lat, z)
        y_max = _lat2tile_y(min_lat, z)
        n = (math.ceil(x_max) - math.floor(x_min)) * (
            math.ceil(y_max) - math.floor(y_min)
        )
        if n <= MAX_TILES:
            return z
    return 12


def render_croqui_satellite_png(
    coords_lonlat: list[tuple[float, float]],
    width: int = 720,
    height: int = 480,
    pad_ratio: float = 0.25,
    marker_size: int = 6,
    font_size: int = 11,
    tile_zoom_override: int | None = None,
) -> bytes | None:
    if len(coords_lonlat) < 3:
        return None

    lons = [c[0] for c in coords_lonlat]
    lats = [c[1] for c in coords_lonlat]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    pad_lon = max(max_lon - min_lon, 1e-5) * pad_ratio
    pad_lat = max(max_lat - min_lat, 1e-5) * pad_ratio
    min_lon -= pad_lon
    max_lon += pad_lon
    min_lat -= pad_lat
    max_lat += pad_lat

    if tile_zoom_override is not None:
        z = max(11, min(MAX_ZOOM_ESRI, tile_zoom_override))
    else:
        z = _pick_zoom(min_lon, max_lon, min_lat, max_lat)

    x_min_f = _lon2tile_x(min_lon, z)
    x_max_f = _lon2tile_x(max_lon, z)
    y_min_f = _lat2tile_y(max_lat, z)
    y_max_f = _lat2tile_y(min_lat, z)
    x_min = math.floor(x_min_f)
    x_max = math.ceil(x_max_f)
    y_min = math.floor(y_min_f)
    y_max = math.ceil(y_max_f)

    full_w = (x_max - x_min) * TILE_SIZE
    full_h = (y_max - y_min) * TILE_SIZE
    canvas = Image.new("RGB", (full_w, full_h), (220, 220, 220))

    try:
        with httpx.Client(timeout=10.0, headers={"User-Agent": "cartorio-mosaico/0.4"}) as client:
            for tx in range(x_min, x_max):
                for ty in range(y_min, y_max):
                    url = ESRI_TILE.format(z=z, x=tx, y=ty)
                    try:
                        r = client.get(url)
                        if r.status_code == 200 and len(r.content) > 0:
                            tile = Image.open(BytesIO(r.content))
                            canvas.paste(
                                tile,
                                ((tx - x_min) * TILE_SIZE, (ty - y_min) * TILE_SIZE),
                            )
                    except Exception:
                        continue
    except Exception:
        return None

    # Recorta na bbox real
    left_px = (x_min_f - x_min) * TILE_SIZE
    top_px = (y_min_f - y_min) * TILE_SIZE
    right_px = (x_max_f - x_min) * TILE_SIZE
    bottom_px = (y_max_f - y_min) * TILE_SIZE
    canvas = canvas.crop(
        (int(left_px), int(top_px), int(right_px), int(bottom_px))
    )
    canvas = canvas.resize((width, height), Image.LANCZOS).convert("RGBA")

    # Overlay polígono e marcos
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def to_px(lon: float, lat: float) -> tuple[float, float]:
        x_norm = (_lon2tile_x(lon, z) - x_min_f) / (x_max_f - x_min_f)
        y_norm = (_lat2tile_y(lat, z) - y_min_f) / (y_max_f - y_min_f)
        return (x_norm * width, y_norm * height)

    pts = [to_px(lon, lat) for lon, lat in coords_lonlat]
    pts_closed = pts + [pts[0]]

    draw.polygon(pts_closed, fill=(255, 107, 53, 90), outline=(255, 107, 53, 255))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(255, 107, 53, 255), width=3)
    draw.line([pts[-1], pts[0]], fill=(255, 107, 53, 255), width=3)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    label_offset = max(font_size - 2, 4)
    for i, (x, y) in enumerate(pts):
        draw.ellipse(
            (x - marker_size, y - marker_size, x + marker_size, y + marker_size),
            fill=(255, 255, 255, 255),
            outline=(255, 107, 53, 255),
            width=2,
        )
        if font:
            draw.text(
                (x + label_offset, y - (font_size + 3)),
                f"M{i}",
                fill=(255, 255, 255, 255),
                font=font,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255),
            )

    out = Image.alpha_composite(canvas, overlay).convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
