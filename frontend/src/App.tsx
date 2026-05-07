import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MlMap, type MapMouseEvent } from "maplibre-gl";

import {
  buscarMosaico,
  criarLote,
  criarMatricula,
  healthCheck,
  listarMatriculas,
  memorialPdfUrl,
  type Matricula,
} from "./api/client";
import {
  computeArea,
  computePerimeter,
  computeSides,
  type LonLat,
} from "./lib/geo";

const FERROS_CENTER: LonLat = [-43.022, -19.234];

const BASEMAPS = {
  esri: {
    label: "Satélite (Esri)",
    tiles: [
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "Tiles © Esri",
  },
  osm: {
    label: "Mapa (OSM)",
    tiles: [
      "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
    ],
    attribution: "© OpenStreetMap contributors",
  },
} as const;

type ApiStatus = "checking" | "ok" | "error";
type FormState = {
  numero: string;
  proprietario_atual_nome: string;
  endereco_logradouro: string;
  area_descrita_texto: string;
  comarca: string;
};
const EMPTY_FORM: FormState = {
  numero: "",
  proprietario_atual_nome: "",
  endereco_logradouro: "",
  area_descrita_texto: "",
  comarca: "Ferros",
};

export default function App() {
  const mapDiv = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const dragRef = useRef<{ idx: number } | null>(null);

  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [vertices, setVertices] = useState<LonLat[]>([]);
  const [drawing, setDrawing] = useState(false);
  const [matriculas, setMatriculas] = useState<Matricula[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [lastLoteId, setLastLoteId] = useState<number | null>(null);

  // Refs to read latest state inside MapLibre handlers
  const stateRef = useRef({ vertices, drawing });
  stateRef.current = { vertices, drawing };

  // Carrega health + matriculas
  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("error"));
    refreshMatriculas();
  }, []);

  function refreshMatriculas() {
    listarMatriculas()
      .then(setMatriculas)
      .catch(() => setMatriculas([]));
  }

  // Setup do mapa (uma vez)
  useEffect(() => {
    if (!mapDiv.current) return;

    const map = new maplibregl.Map({
      container: mapDiv.current,
      style: {
        version: 8,
        sources: {
          esri: {
            type: "raster",
            tiles: [...BASEMAPS.esri.tiles],
            tileSize: 256,
            maxzoom: 19,
            attribution: BASEMAPS.esri.attribution,
          },
        },
        layers: [{ id: "esri", type: "raster", source: "esri" }],
      },
      center: FERROS_CENTER,
      zoom: 14,
      maxZoom: 24,
    });
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }));

    map.on("load", () => {
      map.addSource("lote", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "lote-fill",
        type: "fill",
        source: "lote",
        paint: { "fill-color": "#ff6b35", "fill-opacity": 0.35 },
      });
      map.addLayer({
        id: "lote-line",
        type: "line",
        source: "lote",
        paint: { "line-color": "#ff6b35", "line-width": 2.5 },
      });
      map.addSource("vertices-src", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "vertices-pt",
        type: "circle",
        source: "vertices-src",
        paint: {
          "circle-radius": 6,
          "circle-color": "#fff",
          "circle-stroke-color": "#ff6b35",
          "circle-stroke-width": 2.5,
        },
      });
      map.addLayer({
        id: "vertices-label",
        type: "symbol",
        source: "vertices-src",
        layout: {
          "text-field": ["concat", "M", ["to-string", ["get", "idx"]]],
          "text-size": 12,
          "text-offset": [0, -1.4],
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": "#fff",
          "text-halo-color": "#000",
          "text-halo-width": 1.5,
        },
      });
      // Mosaico — lotes salvos
      map.addSource("mosaico", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer(
        {
          id: "mosaico-fill",
          type: "fill",
          source: "mosaico",
          paint: { "fill-color": "#3399ff", "fill-opacity": 0.2 },
        },
        "lote-fill",
      );
      map.addLayer(
        {
          id: "mosaico-line",
          type: "line",
          source: "mosaico",
          paint: {
            "line-color": "#3399ff",
            "line-width": 1.6,
            "line-dasharray": [2, 2],
          },
        },
        "lote-line",
      );

      loadMosaico();
    });

    map.on("click", (e: MapMouseEvent) => {
      if (!stateRef.current.drawing) return;
      setVertices((prev) => [...prev, [e.lngLat.lng, e.lngLat.lat]]);
    });

    // Hover/drag em vértice
    map.on("mouseenter", "vertices-pt", () => {
      if (stateRef.current.drawing || dragRef.current) return;
      map.getCanvas().style.cursor = "grab";
    });
    map.on("mouseleave", "vertices-pt", () => {
      if (dragRef.current) return;
      map.getCanvas().style.cursor = stateRef.current.drawing ? "crosshair" : "";
    });
    map.on("mousedown", "vertices-pt", (e) => {
      if (stateRef.current.drawing) return;
      e.preventDefault();
      const props = e.features?.[0].properties as { idx?: number } | undefined;
      if (typeof props?.idx === "number") {
        dragRef.current = { idx: props.idx };
        map.getCanvas().style.cursor = "grabbing";
      }
    });
    map.on("mousemove", (e) => {
      if (!dragRef.current) return;
      const idx = dragRef.current.idx;
      setVertices((prev) =>
        prev.map((v, i) => (i === idx ? [e.lngLat.lng, e.lngLat.lat] : v)),
      );
    });
    map.on("mouseup", () => {
      if (!dragRef.current) return;
      dragRef.current = null;
      map.getCanvas().style.cursor = "";
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Atualiza source do polígono ao mudar vertices
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("lote")) return;

    const src = map.getSource("lote") as maplibregl.GeoJSONSource;
    const vsrc = map.getSource("vertices-src") as maplibregl.GeoJSONSource;

    if (vertices.length === 0) {
      src.setData({ type: "FeatureCollection", features: [] });
      vsrc.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    let geom: GeoJSON.Geometry | null;
    if (vertices.length >= 3) {
      geom = {
        type: "Polygon",
        coordinates: [[...vertices, vertices[0]]],
      };
    } else if (vertices.length === 2) {
      geom = { type: "LineString", coordinates: vertices };
    } else {
      geom = null;
    }
    src.setData(
      geom
        ? { type: "Feature", geometry: geom, properties: {} }
        : { type: "FeatureCollection", features: [] },
    );
    vsrc.setData({
      type: "FeatureCollection",
      features: vertices.map((v, i) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: v },
        properties: { idx: i },
      })),
    });
  }, [vertices]);

  // Cursor em modo desenho
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = drawing ? "crosshair" : "";
  }, [drawing]);

  function loadMosaico() {
    const map = mapRef.current;
    if (!map) return;
    buscarMosaico()
      .then((fc) => {
        const src = map.getSource("mosaico") as maplibregl.GeoJSONSource;
        if (src) src.setData(fc);
      })
      .catch(() => {});
  }

  async function handleSearchAddress() {
    const q = (document.getElementById("search-input") as HTMLInputElement)
      ?.value;
    if (!q) return;
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`,
      );
      const data: Array<{ lat: string; lon: string; display_name: string }> =
        await res.json();
      if (!data.length) return;
      mapRef.current?.flyTo({
        center: [parseFloat(data[0].lon), parseFloat(data[0].lat)],
        zoom: 18,
      });
    } catch {
      /* ignore */
    }
  }

  async function handleSave() {
    if (vertices.length < 3 || !form.numero.trim()) {
      alert("Preencha o número da matrícula e desenhe um polígono");
      return;
    }
    setSaving(true);
    try {
      let matricula: Matricula;
      const existing = matriculas.find((m) => m.numero === form.numero);
      if (existing) {
        matricula = existing;
      } else {
        matricula = await criarMatricula({
          numero: form.numero,
          proprietario_atual_nome: form.proprietario_atual_nome || null,
          endereco_logradouro: form.endereco_logradouro || null,
          area_descrita_texto: form.area_descrita_texto || null,
        });
      }
      const lote = await criarLote({
        matricula_id: matricula.id,
        vertices: vertices as [number, number][],
      });
      setLastLoteId(lote.id);
      refreshMatriculas();
      loadMosaico();
      alert(
        `Salvo. Matrícula ${matricula.numero} — Lote #${lote.id} (área ${(
          lote.area_calculada_m2 ?? 0
        ).toFixed(2)} m²)`,
      );
    } catch (e) {
      alert(`Erro ao salvar: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  function handleStart() {
    setVertices([]);
    setDrawing(true);
    setLastLoteId(null);
  }
  function handleFinish() {
    if (vertices.length < 3) {
      alert("Mínimo 3 vértices");
      return;
    }
    setDrawing(false);
  }
  function handleClear() {
    setVertices([]);
    setDrawing(false);
    setLastLoteId(null);
  }
  function handleUndo() {
    setVertices((prev) => prev.slice(0, -1));
  }

  const sides = vertices.length >= 3 ? computeSides(vertices) : [];
  const areaM2 = computeArea(vertices);
  const perimM = computePerimeter(vertices);

  return (
    <div className="app">
      <header>
        <h1>Cartório Mosaico</h1>
        <span className={`status status-${apiStatus}`}>
          API:{" "}
          {apiStatus === "checking"
            ? "..."
            : apiStatus === "ok"
              ? "online"
              : "offline (rode o backend)"}
        </span>
      </header>
      <div className="layout">
        <aside className="panel">
          <h2>Buscar endereço</h2>
          <div className="row">
            <input id="search-input" placeholder="ex: Praça do Centro, Ferros, MG" />
            <button onClick={handleSearchAddress}>Ir</button>
          </div>

          <h2>Matrícula</h2>
          <label>
            Número
            <input
              value={form.numero}
              onChange={(e) => setForm({ ...form, numero: e.target.value })}
            />
          </label>
          <label>
            Proprietário(a)
            <input
              value={form.proprietario_atual_nome}
              onChange={(e) =>
                setForm({ ...form, proprietario_atual_nome: e.target.value })
              }
            />
          </label>
          <label>
            Endereço
            <input
              value={form.endereco_logradouro}
              onChange={(e) =>
                setForm({ ...form, endereco_logradouro: e.target.value })
              }
            />
          </label>
          <label>
            Descrição textual
            <textarea
              rows={3}
              value={form.area_descrita_texto}
              onChange={(e) =>
                setForm({ ...form, area_descrita_texto: e.target.value })
              }
            />
          </label>

          <h2>Desenho do lote</h2>
          <div>
            <button onClick={handleStart} disabled={drawing}>
              Iniciar desenho
            </button>
            <button onClick={handleFinish} disabled={!drawing}>
              Finalizar
            </button>
            <button onClick={handleUndo} disabled={vertices.length === 0}>
              Desfazer
            </button>
            <button onClick={handleClear} className="danger">
              Limpar
            </button>
          </div>

          <h2>Métricas</h2>
          <dl>
            <dt>Vértices</dt>
            <dd>{vertices.length}</dd>
            <dt>Área</dt>
            <dd>
              {vertices.length >= 3
                ? `${areaM2.toFixed(2)} m² (${(areaM2 / 10000).toFixed(4)} ha)`
                : "—"}
            </dd>
            <dt>Perímetro</dt>
            <dd>
              {vertices.length >= 3 ? `${perimM.toFixed(2)} m` : "—"}
            </dd>
          </dl>
          {sides.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Lado</th>
                  <th>Distância</th>
                  <th>Azimute</th>
                </tr>
              </thead>
              <tbody>
                {sides.map((s) => (
                  <tr key={`${s.from}-${s.to}`}>
                    <td>
                      M{s.from}→M{s.to}
                    </td>
                    <td>{s.distM.toFixed(2)} m</td>
                    <td>{s.azDms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h2>Salvar / Memorial</h2>
          <button
            onClick={handleSave}
            disabled={saving || vertices.length < 3 || !form.numero.trim()}
            className="primary"
          >
            {saving ? "Salvando..." : "Salvar matrícula + lote"}
          </button>
          {lastLoteId !== null && (
            <p style={{ marginTop: 8 }}>
              <a
                href={memorialPdfUrl(lastLoteId)}
                target="_blank"
                rel="noopener"
              >
                Baixar memorial PDF do lote #{lastLoteId}
              </a>
            </p>
          )}

          <h2>Matrículas no banco</h2>
          {matriculas.length === 0 ? (
            <p style={{ color: "#888", fontSize: 13 }}>
              — nenhuma matrícula —
            </p>
          ) : (
            <ul className="matriculas-list">
              {matriculas.slice(0, 20).map((m) => (
                <li key={m.id}>
                  <strong>{m.numero}</strong>
                  {m.proprietario_atual_nome
                    ? ` — ${m.proprietario_atual_nome}`
                    : ""}
                  <span className={`badge badge-${m.status_geometria}`}>
                    {m.status_geometria}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </aside>
        <div ref={mapDiv} className="map" />
      </div>
    </div>
  );
}
