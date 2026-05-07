import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { healthCheck } from "./api/client";

const FERROS_CENTER: [number, number] = [-43.022, -19.234];

type ApiStatus = "checking" | "ok" | "error";

export default function App() {
  const mapDiv = useRef<HTMLDivElement>(null);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    if (!mapDiv.current) return;

    const map = new maplibregl.Map({
      container: mapDiv.current,
      style: {
        version: 8,
        sources: {
          esri: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 19,
            attribution: "Tiles © Esri",
          },
        },
        layers: [{ id: "esri", type: "raster", source: "esri" }],
      },
      center: FERROS_CENTER,
      zoom: 17,
      maxZoom: 24,
    });
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }));

    return () => {
      map.remove();
    };
  }, []);

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("error"));
  }, []);

  return (
    <div className="app">
      <header>
        <h1>Cartório Mosaico</h1>
        <span className={`status status-${apiStatus}`}>
          API:{" "}
          {apiStatus === "checking"
            ? "verificando..."
            : apiStatus === "ok"
              ? "online"
              : "offline (rode o backend)"}
        </span>
      </header>
      <div className="layout">
        <aside className="panel">
          <h2>V0.1 — Frontend mínimo</h2>
          <p>
            Esta é a base do frontend de produção. O protótipo completo (com
            desenho de polígono, métricas em tempo real, geração de memorial e
            impressão) está em <code>prototype/index.html</code>.
          </p>
          <p>
            <strong>Próximos passos:</strong>
          </p>
          <ul>
            <li>Portar editor de polígono do protótipo</li>
            <li>
              Conectar ao backend: <code>/api/matriculas</code>,{" "}
              <code>/api/lotes</code>, <code>/api/mosaico</code>,{" "}
              <code>/api/memoriais</code>
            </li>
            <li>Login + JWT</li>
            <li>Vista de mosaico com detecção de conflitos</li>
          </ul>
        </aside>
        <div ref={mapDiv} className="map" />
      </div>
    </div>
  );
}
