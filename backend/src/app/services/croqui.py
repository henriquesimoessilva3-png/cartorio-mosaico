"""Renderização SVG do croqui do lote — embutido no PDF do memorial."""
from __future__ import annotations


def render_croqui_svg(
    coords_utm: list[tuple[float, float]],
    width: int = 620,
    height: int = 400,
    pad: int = 36,
    marker_size: int = 5,
    font_size: int = 11,
) -> str:
    """SVG simples do polígono em UTM com marcos numerados e bússola N.

    Todos os parâmetros visuais são configuráveis pelo caller (UI/API) — o
    endpoint do memorial faz clamp dos valores para evitar marcos invisíveis.
    """
    if not coords_utm:
        return ""

    min_e = min(c[0] for c in coords_utm)
    max_e = max(c[0] for c in coords_utm)
    min_n = min(c[1] for c in coords_utm)
    max_n = max(c[1] for c in coords_utm)
    span_e = max(max_e - min_e, 1.0)
    span_n = max(max_n - min_n, 1.0)
    scale = min((width - 2 * pad) / span_e, (height - 2 * pad) / span_n)

    def t(e: float, n: float) -> tuple[float, float]:
        return ((e - min_e) * scale + pad, height - ((n - min_n) * scale + pad))

    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (t(*c) for c in coords_utm))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'style="background:#f5f5f5;border:1px solid #999">',
        f'<polygon points="{pts}" fill="#ff6b35" fill-opacity="0.25" '
        'stroke="#ff6b35" stroke-width="2"/>',
    ]

    label_offset = max(font_size - 2, 4)
    for i, c in enumerate(coords_utm):
        x, y = t(*c)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{marker_size}" fill="#fff" '
            'stroke="#ff6b35" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + label_offset:.1f}" y="{y - label_offset:.1f}" '
            f'font-size="{font_size}" font-family="Arial" font-weight="bold">'
            f'M{i}</text>'
        )

    cx, cy = width - 36, 36
    parts.append(
        f'<g transform="translate({cx},{cy})">'
        '<circle r="14" fill="#fff" stroke="#666"/>'
        '<line x1="0" y1="-12" x2="0" y2="12" stroke="#666" stroke-width="1.5"/>'
        '<polygon points="0,-13 -3,-7 3,-7" fill="#666"/>'
        '<text x="0" y="-16" text-anchor="middle" font-size="10" '
        'font-family="Arial" font-weight="bold">N</text>'
        "</g>"
    )

    parts.append("</svg>")
    return "".join(parts)
