import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MlMap, type MapMouseEvent } from "maplibre-gl";

import {
  atualizarUsuario,
  baixarMemorialPdf,
  buscarConflitos,
  buscarMosaico,
  criarLote,
  criarMatricula,
  criarUsuario,
  desativarUsuario,
  getToken,
  healthCheck,
  listarAuditorias,
  listarMatriculas,
  listarUsuarios,
  login as apiLogin,
  logout as apiLogout,
  lotesPorMatricula,
  me as apiMe,
  obterAuditoria,
  previewCroquiBlob,
  validacaoTextual,
  type AuditoriaDetail,
  type AuditoriaFilters,
  type AuditoriaListItem,
  type Conflito,
  type Lote,
  type Matricula,
  type PdfOptions,
  type User,
  type UserCreate,
  type ValidacaoTextual,
} from "./api/client";
import {
  computeArea,
  computePerimeter,
  computeSides,
  type LonLat,
} from "./lib/geo";

const FERROS_CENTER: LonLat = [-43.022, -19.234];
const DRAFT_KEY = (userId: number) => `cartorio-draft:${userId}`;

// Auto-login dev: pula a tela de login. Backend continua exigindo JWT
// (audit log precisa do user_id), mas o usuário não vê a tela.
const DEV_AUTOLOGIN = {
  email: "henrique@local.test",
  password: "minhasenha-12345",
};

function computeBoundsFromFeatures(
  features: GeoJSON.Feature[],
): [[number, number], [number, number]] | null {
  let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
  function visit(coords: unknown): void {
    if (typeof coords === "number") return;
    if (Array.isArray(coords) && typeof coords[0] === "number") {
      const [lng, lat] = coords as [number, number];
      if (lng < minLng) minLng = lng;
      if (lat < minLat) minLat = lat;
      if (lng > maxLng) maxLng = lng;
      if (lat > maxLat) maxLat = lat;
      return;
    }
    if (Array.isArray(coords)) coords.forEach(visit);
  }
  for (const f of features) {
    if (f.geometry && "coordinates" in f.geometry) {
      visit(f.geometry.coordinates);
    }
  }
  if (!isFinite(minLng)) return null;
  return [[minLng, minLat], [maxLng, maxLat]];
}

const BASEMAPS = {
  esri: {
    label: "Satélite",
    tiles: [
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "Tiles © Esri",
  },
  osm: {
    label: "Mapa OSM",
    tiles: [
      "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
    ],
    attribution: "© OpenStreetMap contributors",
  },
} as const;

type FormState = {
  numero: string;
  proprietario_atual_nome: string;
  endereco_logradouro: string;
  area_descrita_texto: string;
};
const EMPTY_FORM: FormState = {
  numero: "",
  proprietario_atual_nome: "",
  endereco_logradouro: "",
  area_descrita_texto: "",
};

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [bootErr, setBootErr] = useState<string | null>(null);

  useEffect(() => {
    async function bootstrap() {
      if (getToken()) {
        try {
          const u = await apiMe();
          setUser(u);
          return;
        } catch {
          apiLogout();
        }
      }
      try {
        const { user: u } = await apiLogin(
          DEV_AUTOLOGIN.email,
          DEV_AUTOLOGIN.password,
        );
        setUser(u);
      } catch (e) {
        setBootErr(String(e));
      }
    }
    void bootstrap().finally(() => setAuthChecking(false));
  }, []);

  if (authChecking) {
    return <div className="full-center">Conectando…</div>;
  }
  if (!user) {
    return (
      <div className="full-center">
        <div className="login-card">
          <h1>Cartório Mosaico</h1>
          <p className="err">Não foi possível conectar.</p>
          <p className="muted small">{bootErr ?? "—"}</p>
          <p className="muted small">
            Verifique se o backend está rodando e se o usuário admin existe.
          </p>
        </div>
      </div>
    );
  }
  return <Editor user={user} />;
}

function Editor({ user }: { user: User }) {
  const mapDiv = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const dragRef = useRef<{ idx: number } | null>(null);

  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [vertices, setVertices] = useState<LonLat[]>([]);
  const [drawing, setDrawing] = useState(false);
  const [matriculas, setMatriculas] = useState<Matricula[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [lastLoteId, setLastLoteId] = useState<number | null>(null);
  const [history, setHistory] = useState<Lote[]>([]);
  const [conflitosOpen, setConflitosOpen] = useState(false);
  const [conflitos, setConflitos] = useState<Conflito[]>([]);
  const [conflitosLoading, setConflitosLoading] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [auditoriaOpen, setAuditoriaOpen] = useState(false);
  const [memoriaisOpen, setMemoriaisOpen] = useState(false);
  const [pdfDialogLoteId, setPdfDialogLoteId] = useState<number | null>(null);
  const [validacao, setValidacao] = useState<ValidacaoTextual | null>(null);

  const stateRef = useRef({ vertices, drawing });
  stateRef.current = { vertices, drawing };

  useEffect(() => {
    healthCheck().then(() => setApiOk(true)).catch(() => setApiOk(false));
    refreshMatriculas();
    // Restaura desenho em andamento da última sessão (se houver).
    try {
      const raw = localStorage.getItem(DRAFT_KEY(user.id));
      if (raw) {
        const parsed = JSON.parse(raw) as { vertices?: LonLat[]; form?: FormState };
        if (parsed.vertices && parsed.vertices.length > 0) {
          setVertices(parsed.vertices);
          if (parsed.form) setForm(parsed.form);
        }
      }
    } catch {
      // localStorage corrompido — ignora.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persiste desenho em andamento no localStorage (auto-save).
  useEffect(() => {
    if (vertices.length === 0 && !form.numero.trim()) {
      localStorage.removeItem(DRAFT_KEY(user.id));
      return;
    }
    try {
      localStorage.setItem(
        DRAFT_KEY(user.id),
        JSON.stringify({ vertices, form }),
      );
    } catch {
      // quota cheia — ignora.
    }
  }, [vertices, form, user.id]);

  function refreshMatriculas() {
    listarMatriculas()
      .then(setMatriculas)
      .catch(() => setMatriculas([]));
  }

  // Carrega histórico ao mudar número de matrícula no form
  useEffect(() => {
    const m = matriculas.find((x) => x.numero === form.numero);
    if (!m) {
      setHistory([]);
      return;
    }
    lotesPorMatricula(m.id).then(setHistory).catch(() => setHistory([]));
  }, [form.numero, matriculas]);

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
      map.addSource("mosaico", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "mosaico-fill",
        type: "fill",
        source: "mosaico",
        paint: {
          "fill-color": [
            "match",
            ["get", "status"],
            "validado_art",
            "#2ecc71",
            "revisado",
            "#3498db",
            "rascunho",
            "#f39c12",
            "#bdc3c7",
          ],
          "fill-opacity": 0.25,
        },
      });
      map.addLayer({
        id: "mosaico-line",
        type: "line",
        source: "mosaico",
        paint: { "line-color": "#3498db", "line-width": 1.6 },
      });

      map.addSource("lote", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "lote-fill",
        type: "fill",
        source: "lote",
        paint: { "fill-color": "#ff6b35", "fill-opacity": 0.4 },
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

      loadMosaico();
    });

    map.on("click", (e: MapMouseEvent) => {
      if (!stateRef.current.drawing) return;
      // Se o clique foi em cima de um vértice existente, não adiciona — o
      // drag handler vai assumir.
      const hits = map.queryRenderedFeatures(e.point, { layers: ["vertices-pt"] });
      if (hits.length > 0) return;
      setVertices((prev) => [...prev, [e.lngLat.lng, e.lngLat.lat]]);
    });

    map.on("mouseenter", "vertices-pt", () => {
      if (dragRef.current) return;
      map.getCanvas().style.cursor = "grab";
    });
    map.on("mouseleave", "vertices-pt", () => {
      if (dragRef.current) return;
      map.getCanvas().style.cursor = stateRef.current.drawing ? "crosshair" : "";
    });
    map.on("mousedown", "vertices-pt", (e) => {
      // Permite drag tanto durante quanto após o desenho.
      e.preventDefault();
      const props = e.features?.[0].properties as { idx?: number } | undefined;
      if (typeof props?.idx === "number") {
        dragRef.current = { idx: props.idx };
        map.getCanvas().style.cursor = "grabbing";
        map.dragPan.disable();
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
      map.dragPan.enable();
    });
    // Suporte a touch (mobile) — espelha o mesmo padrão do mouse.
    map.on("touchstart", "vertices-pt", (e) => {
      if (e.points.length !== 1) return;
      e.preventDefault();
      const props = e.features?.[0].properties as { idx?: number } | undefined;
      if (typeof props?.idx === "number") {
        dragRef.current = { idx: props.idx };
        map.dragPan.disable();
      }
    });
    map.on("touchmove", (e) => {
      if (!dragRef.current || e.points.length !== 1) return;
      e.preventDefault();
      const idx = dragRef.current.idx;
      setVertices((prev) =>
        prev.map((v, i) => (i === idx ? [e.lngLat.lng, e.lngLat.lat] : v)),
      );
    });
    map.on("touchend", () => {
      if (!dragRef.current) return;
      dragRef.current = null;
      map.dragPan.enable();
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

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
      geom = { type: "Polygon", coordinates: [[...vertices, vertices[0]]] };
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

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.getCanvas().style.cursor = drawing ? "crosshair" : "";
  }, [drawing]);

  function loadMosaico(autoFit: boolean = true) {
    const map = mapRef.current;
    if (!map) return;
    buscarMosaico()
      .then((fc) => {
        const src = map.getSource("mosaico") as maplibregl.GeoJSONSource;
        if (src) src.setData(fc);
        if (autoFit && fc.features.length > 0) {
          const bounds = computeBoundsFromFeatures(fc.features);
          if (bounds) {
            map.fitBounds(bounds, { padding: 60, maxZoom: 19, duration: 600 });
          }
        }
      })
      .catch(() => {});
  }

  function flyToMatricula(matriculaId: number) {
    const map = mapRef.current;
    if (!map) return;
    const src = map.getSource("mosaico") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    const fc = (src as unknown as { _data?: GeoJSON.FeatureCollection })._data;
    const feat = fc?.features.find(
      (f) => (f.properties as { matricula_id?: number })?.matricula_id === matriculaId,
    );
    if (!feat) return;
    const b = computeBoundsFromFeatures([feat]);
    if (b) map.fitBounds(b, { padding: 80, maxZoom: 21, duration: 700 });
  }

  async function handleSearchAddress() {
    const q = (document.getElementById("search-input") as HTMLInputElement)?.value;
    if (!q) return;
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`,
      );
      const data: Array<{ lat: string; lon: string }> = await res.json();
      if (!data.length) return;
      mapRef.current?.flyTo({
        center: [parseFloat(data[0].lon), parseFloat(data[0].lat)],
        zoom: 18,
      });
    } catch { /* ignore */ }
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
      loadMosaico(false); // não reposiciona — usuário acabou de desenhar aqui
      // Limpa o rascunho persistido após salvar com sucesso.
      localStorage.removeItem(DRAFT_KEY(user.id));
      alert(
        `Salvo. Matrícula ${matricula.numero} — Lote #${lote.id} v${lote.versao} (área ${(
          lote.area_calculada_m2 ?? 0
        ).toFixed(2)} m²)`,
      );
    } catch (e) {
      alert(`Erro ao salvar: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleConflitos() {
    setConflitosOpen(true);
    setConflitosLoading(true);
    try {
      const r = await buscarConflitos();
      setConflitos(r.overlaps);
    } catch (e) {
      alert(`Erro: ${e}`);
    } finally {
      setConflitosLoading(false);
    }
  }

  function handleBaixarPdf(loteId: number) {
    // Abre dialog de configuração; o download em si acontece dentro do dialog.
    setPdfDialogLoteId(loteId);
  }

  async function handleValidar(loteId: number) {
    try {
      const v = await validacaoTextual(loteId);
      setValidacao(v);
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  function loadVersionToEditor(lote: Lote) {
    if (!lote.vertices_jsonb) return;
    const vs: LonLat[] = lote.vertices_jsonb.map((v) => [v.lon, v.lat]);
    setVertices(vs);
    setDrawing(false);
    if (vs.length) {
      const lons = vs.map((v) => v[0]);
      const lats = vs.map((v) => v[1]);
      mapRef.current?.fitBounds(
        [
          [Math.min(...lons), Math.min(...lats)],
          [Math.max(...lons), Math.max(...lats)],
        ],
        { padding: 60, maxZoom: 19 },
      );
    }
  }

  const sides = vertices.length >= 3 ? computeSides(vertices) : [];
  const areaM2 = computeArea(vertices);
  const perimM = computePerimeter(vertices);

  return (
    <div className="app">
      <header>
        <h1>Cartório Mosaico</h1>
        <div className="header-right">
          <span className={`status ${apiOk === true ? "status-ok" : apiOk === false ? "status-error" : "status-checking"}`}>
            API: {apiOk === true ? "online" : apiOk === false ? "offline" : "..."}
          </span>
          <span className="user-chip">
            {user.nome} <small>({user.role})</small>
            {user.tenant?.nome && (
              <small style={{ marginLeft: 6, opacity: 0.7 }}>· {user.tenant.nome}</small>
            )}
          </span>
          <button onClick={() => setMemoriaisOpen(true)} className="link-btn">
            Memoriais
          </button>
          {user.role === "admin" && (
            <>
              <button onClick={() => setAdminOpen(true)} className="link-btn">
                Usuários
              </button>
              <button onClick={() => setAuditoriaOpen(true)} className="link-btn">
                Auditoria
              </button>
            </>
          )}
        </div>
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
              onChange={(e) => setForm({ ...form, proprietario_atual_nome: e.target.value })}
            />
          </label>
          <label>
            Endereço
            <input
              value={form.endereco_logradouro}
              onChange={(e) => setForm({ ...form, endereco_logradouro: e.target.value })}
            />
          </label>
          <label>
            Descrição textual
            <textarea
              rows={3}
              value={form.area_descrita_texto}
              onChange={(e) => setForm({ ...form, area_descrita_texto: e.target.value })}
            />
          </label>

          {history.length > 0 && (
            <>
              <h2>Histórico de versões</h2>
              <ul className="history">
                {history.map((h) => (
                  <li key={h.id}>
                    <span>
                      <strong>v{h.versao}</strong>{" "}
                      <small>{new Date(h.criado_em).toLocaleString("pt-BR")}</small>
                      <br />
                      <small>
                        {(h.area_calculada_m2 ?? 0).toFixed(2)} m² ·{" "}
                        {(h.perimetro_m ?? 0).toFixed(2)} m
                      </small>
                    </span>
                    <span>
                      <button onClick={() => loadVersionToEditor(h)}>Carregar</button>
                      <button onClick={() => handleBaixarPdf(h.id)}>PDF</button>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}

          <h2>Desenho do lote</h2>
          <div>
            <button onClick={() => { setVertices([]); setDrawing(true); setLastLoteId(null); }} disabled={drawing}>
              Iniciar
            </button>
            <button onClick={() => { if (vertices.length < 3) { alert("Mínimo 3"); return; } setDrawing(false); }} disabled={!drawing}>
              Finalizar
            </button>
            <button onClick={() => setVertices((p) => p.slice(0, -1))} disabled={vertices.length === 0}>
              Desfazer
            </button>
            <button onClick={() => { setVertices([]); setDrawing(false); setLastLoteId(null); }} className="danger">
              Limpar
            </button>
          </div>

          <h2>Métricas</h2>
          <dl>
            <dt>Vértices</dt><dd>{vertices.length}</dd>
            <dt>Área</dt>
            <dd>{vertices.length >= 3 ? `${areaM2.toFixed(2)} m² (${(areaM2 / 10000).toFixed(4)} ha)` : "—"}</dd>
            <dt>Perímetro</dt>
            <dd>{vertices.length >= 3 ? `${perimM.toFixed(2)} m` : "—"}</dd>
          </dl>
          {sides.length > 0 && (
            <table>
              <thead><tr><th>Lado</th><th>Distância</th><th>Azimute</th></tr></thead>
              <tbody>
                {sides.map((s) => (
                  <tr key={`${s.from}-${s.to}`}>
                    <td>M{s.from}→M{s.to}</td>
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
            <div style={{ marginTop: 8 }}>
              <button onClick={() => handleBaixarPdf(lastLoteId)}>
                Baixar memorial PDF do lote #{lastLoteId}
              </button>
              <button onClick={() => handleValidar(lastLoteId)}>
                Validar contra texto
              </button>
            </div>
          )}
          {validacao && (
            <div className="validacao">
              <h3>Validação textual</h3>
              {validacao.avisos.length > 0 ? (
                <ul className="avisos">
                  {validacao.avisos.map((a, i) => (
                    <li key={i}>⚠ {a}</li>
                  ))}
                </ul>
              ) : validacao.numeros_extraidos.length > 0 ? (
                <p className="ok">Todas as medidas batem (tolerância 15%).</p>
              ) : (
                <p className="muted small">
                  Nenhuma medida explícita encontrada no texto.
                </p>
              )}
              {validacao.confrontantes_textuais.length > 0 && (
                <>
                  <h4>Confrontantes detectados no texto</h4>
                  <ul className="confrontantes-textuais">
                    {validacao.confrontantes_textuais.map((c) => (
                      <li key={c.lado}>
                        <strong>{c.lado}:</strong> {c.descricao}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <button
                onClick={() => setValidacao(null)}
                className="link-btn"
                style={{ marginTop: 6, fontSize: 11 }}
              >
                fechar
              </button>
            </div>
          )}

          <h2>Mosaico da circunscrição</h2>
          <div>
            <button onClick={() => loadMosaico(true)}>Recarregar mosaico</button>
            <button onClick={handleConflitos}>Detectar conflitos</button>
          </div>
          <p className="muted small">
            Cores no mapa: cinza = rascunho, azul = revisado, verde = validado ART
          </p>

          <h2>Matrículas no banco ({matriculas.length})</h2>
          {matriculas.length === 0 ? (
            <p style={{ color: "#888", fontSize: 13 }}>— nenhuma —</p>
          ) : (
            <ul className="matriculas-list">
              {matriculas.slice(0, 50).map((m) => (
                <li
                  key={m.id}
                  onClick={() => {
                    setForm((f) => ({ ...f, numero: m.numero }));
                    flyToMatricula(m.id);
                  }}
                  title="Clique para selecionar e voar até o lote no mapa"
                >
                  <strong>{m.numero}</strong>
                  {m.proprietario_atual_nome ? ` — ${m.proprietario_atual_nome}` : ""}
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

      {conflitosOpen && (
        <div className="dialog-backdrop" onClick={() => setConflitosOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h2>Conflitos detectados</h2>
            {conflitosLoading ? (
              <p>Calculando...</p>
            ) : conflitos.length === 0 ? (
              <p className="muted">Nenhuma sobreposição detectada (&gt; 0,5 m²).</p>
            ) : (
              <table>
                <thead>
                  <tr><th>Lote A</th><th>Lote B</th><th>Sobreposição</th></tr>
                </thead>
                <tbody>
                  {conflitos.map((c, i) => (
                    <tr key={i}>
                      <td>#{c.lote_a} (mat {c.matricula_a})</td>
                      <td>#{c.lote_b} (mat {c.matricula_b})</td>
                      <td>{c.area_overlap_m2.toFixed(2)} m²</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div style={{ textAlign: "right", marginTop: 12 }}>
              <button onClick={() => setConflitosOpen(false)}>Fechar</button>
            </div>
          </div>
        </div>
      )}

      {adminOpen && (
        <AdminDialog onClose={() => setAdminOpen(false)} currentUserId={user.id} />
      )}

      {auditoriaOpen && (
        <AuditoriaDialog onClose={() => setAuditoriaOpen(false)} />
      )}

      {pdfDialogLoteId !== null && (
        <PdfConfigDialog
          loteId={pdfDialogLoteId}
          userId={user.id}
          onClose={() => setPdfDialogLoteId(null)}
        />
      )}

      {memoriaisOpen && (
        <MemoriaisDialog
          onClose={() => setMemoriaisOpen(false)}
          onFlyTo={(mid) => {
            flyToMatricula(mid);
            setMemoriaisOpen(false);
          }}
          onBaixarPdf={(loteId) => {
            setMemoriaisOpen(false);
            handleBaixarPdf(loteId);
          }}
        />
      )}
    </div>
  );
}

type MemorialItem = {
  lote_id: number;
  matricula_id: number;
  matricula_numero: string;
  proprietario: string | null;
  versao: number;
  area_m2: number;
  perimetro_m: number;
  criado_em: string | null;
  status: string;
};

function MemoriaisDialog({
  onClose,
  onFlyTo,
  onBaixarPdf,
}: {
  onClose: () => void;
  onFlyTo: (matriculaId: number) => void;
  onBaixarPdf: (loteId: number) => void;
}) {
  const [items, setItems] = useState<MemorialItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [busca, setBusca] = useState("");

  useEffect(() => {
    setLoading(true);
    buscarMosaico()
      .then((fc) => {
        const list = fc.features
          .map((f) => f.properties as unknown as MemorialItem)
          .sort((a, b) => (b.criado_em ?? "").localeCompare(a.criado_em ?? ""));
        setItems(list);
      })
      .catch((e) => alert(`Erro: ${e}`))
      .finally(() => setLoading(false));
  }, []);

  const q = busca.trim().toLowerCase();
  const filtered = items.filter((i) => {
    if (statusFilter && i.status !== statusFilter) return false;
    if (q) {
      const hay = `${i.matricula_numero} ${i.proprietario ?? ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog dialog-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Memoriais ({items.length})</h2>
        <p className="muted small" style={{ marginTop: -4 }}>
          Versão mais recente de cada matrícula. Cada linha = um lote
          geometrizado com PDF disponível.
        </p>
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          <input
            placeholder="buscar matrícula ou proprietário…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">— todos os status —</option>
            <option value="rascunho">rascunho</option>
            <option value="revisado">revisado</option>
            <option value="validado_art">validado ART</option>
          </select>
        </div>
        {loading ? (
          <p>Carregando…</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Matrícula</th>
                  <th>Proprietário</th>
                  <th>v</th>
                  <th>Área (m²)</th>
                  <th>Perím. (m)</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((it) => (
                  <tr key={it.lote_id}>
                    <td>
                      {it.criado_em
                        ? new Date(it.criado_em).toLocaleString("pt-BR")
                        : "—"}
                    </td>
                    <td>
                      <strong>{it.matricula_numero}</strong>
                    </td>
                    <td>{it.proprietario || <em>—</em>}</td>
                    <td>v{it.versao}</td>
                    <td>{it.area_m2.toFixed(2)}</td>
                    <td>{it.perimetro_m.toFixed(2)}</td>
                    <td>
                      <span className={`badge badge-${it.status}`}>
                        {it.status}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => onFlyTo(it.matricula_id)}>
                        Voar
                      </button>
                      <button onClick={() => onBaixarPdf(it.lote_id)}>
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8}>
                      <em>Nenhum memorial encontrado.</em>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <p className="muted small" style={{ marginTop: 8 }}>
              Mostrando {filtered.length} de {items.length}.
            </p>
          </>
        )}
        <div style={{ textAlign: "right", marginTop: 12 }}>
          <button onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  );
}

const DEFAULT_PDF_OPTS: PdfOptions = {
  croqui_width: 620,
  croqui_height: 400,
  croqui_pad: 36,
  marker_size: 5,
  font_size: 11,
  page_margin_cm: 2,
  usar_satelite: false,
};

function _presetKey(userId: number): string {
  return `pdf-preset:${userId}`;
}

function _loadPreset(userId: number): PdfOptions {
  try {
    const raw = localStorage.getItem(_presetKey(userId));
    if (!raw) return { ...DEFAULT_PDF_OPTS };
    return { ...DEFAULT_PDF_OPTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_PDF_OPTS };
  }
}

function PdfConfigDialog({
  loteId,
  userId,
  onClose,
}: {
  loteId: number;
  userId: number;
  onClose: () => void;
}) {
  const [opts, setOpts] = useState<PdfOptions>(() => _loadPreset(userId));
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const debounceRef = useRef<number | null>(null);

  // Persistir preset on change
  useEffect(() => {
    try {
      localStorage.setItem(_presetKey(userId), JSON.stringify(opts));
    } catch {
      // localStorage cheio ou bloqueado — silencioso.
    }
  }, [opts, userId]);

  // Debounced preview refresh — só pra modo SVG (rápido). Satélite carrega
  // só sob clique explícito pra não estourar o orçamento de tiles.
  useEffect(() => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    if (opts.usar_satelite) return; // não auto-refresh em satélite
    debounceRef.current = window.setTimeout(() => {
      void loadPreview();
    }, 400);
    return () => {
      if (debounceRef.current !== null) window.clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    opts.croqui_width,
    opts.croqui_height,
    opts.croqui_pad,
    opts.marker_size,
    opts.font_size,
    opts.usar_satelite,
  ]);

  async function loadPreview() {
    setPreviewLoading(true);
    try {
      const blob = await previewCroquiBlob(loteId, opts);
      const url = URL.createObjectURL(blob);
      setPreviewUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return url;
      });
    } catch (e) {
      console.warn("Preview falhou:", e);
    } finally {
      setPreviewLoading(false);
    }
  }

  // Cleanup blob ao fechar
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function handleDownload() {
    setDownloading(true);
    try {
      const blob = await baixarMemorialPdf(loteId, opts);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      onClose();
    } catch (e) {
      alert(`Erro: ${e}`);
    } finally {
      setDownloading(false);
    }
  }

  function set<K extends keyof PdfOptions>(key: K, val: PdfOptions[K]) {
    setOpts((o) => ({ ...o, [key]: val }));
  }

  function resetPreset() {
    setOpts({ ...DEFAULT_PDF_OPTS });
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog dialog-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Configurar PDF do memorial</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label>
              Largura do croqui ({opts.croqui_width}px)
              <input
                type="range"
                min={320}
                max={1200}
                step={10}
                value={opts.croqui_width ?? 620}
                onChange={(e) => set("croqui_width", Number(e.target.value))}
              />
            </label>
            <label>
              Altura do croqui ({opts.croqui_height}px)
              <input
                type="range"
                min={240}
                max={900}
                step={10}
                value={opts.croqui_height ?? 400}
                onChange={(e) => set("croqui_height", Number(e.target.value))}
              />
            </label>
            <label>
              Padding interno ({opts.croqui_pad}px)
              <input
                type="range"
                min={0}
                max={120}
                step={2}
                value={opts.croqui_pad ?? 36}
                onChange={(e) => set("croqui_pad", Number(e.target.value))}
              />
            </label>
            <label>
              Tamanho do marco ({opts.marker_size}px)
              <input
                type="range"
                min={2}
                max={20}
                step={1}
                value={opts.marker_size ?? 5}
                onChange={(e) => set("marker_size", Number(e.target.value))}
              />
            </label>
            <label>
              Tamanho da fonte ({opts.font_size}pt)
              <input
                type="range"
                min={6}
                max={24}
                step={1}
                value={opts.font_size ?? 11}
                onChange={(e) => set("font_size", Number(e.target.value))}
              />
            </label>
            <label>
              Margem da página ({opts.page_margin_cm}cm)
              <input
                type="range"
                min={0.5}
                max={5}
                step={0.1}
                value={opts.page_margin_cm ?? 2}
                onChange={(e) => set("page_margin_cm", Number(e.target.value))}
              />
            </label>
            <label style={{ display: "block", marginTop: 8 }}>
              <input
                type="checkbox"
                checked={!!opts.usar_satelite}
                onChange={(e) => set("usar_satelite", e.target.checked)}
              />{" "}
              Usar fundo de satélite (Esri)
            </label>
            {opts.usar_satelite && (
              <button onClick={() => void loadPreview()} disabled={previewLoading} style={{ marginTop: 4 }}>
                {previewLoading ? "Carregando…" : "Atualizar preview com satélite"}
              </button>
            )}
            <div style={{ marginTop: 12 }}>
              <button onClick={resetPreset}>Restaurar padrão</button>
            </div>
          </div>
          <div>
            <p style={{ margin: 0 }}>
              <strong>Preview do croqui</strong>
              {previewLoading && <small> · atualizando…</small>}
            </p>
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="Preview do croqui"
                style={{
                  width: "100%",
                  border: "1px solid #ccc",
                  marginTop: 6,
                  background: "#f5f5f5",
                }}
              />
            ) : (
              <p>
                <em>O preview aparecerá aqui.</em>
              </p>
            )}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <button onClick={onClose}>Cancelar</button>
          <button className="primary" onClick={handleDownload} disabled={downloading}>
            {downloading ? "Gerando PDF…" : "Baixar PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AuditoriaDialog({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<AuditoriaListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<AuditoriaFilters>({ limit: 50, offset: 0 });
  const [detail, setDetail] = useState<AuditoriaDetail | null>(null);

  function refresh(next: AuditoriaFilters = filters) {
    setLoading(true);
    listarAuditorias(next)
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
      })
      .catch((e) => alert(`Erro: ${e}`))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.limit, filters.offset]);

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    refresh({ ...filters, offset: 0 });
    setFilters((f) => ({ ...f, offset: 0 }));
  }

  function nextPage() {
    setFilters((f) => ({ ...f, offset: (f.offset ?? 0) + (f.limit ?? 50) }));
  }
  function prevPage() {
    setFilters((f) => ({
      ...f,
      offset: Math.max(0, (f.offset ?? 0) - (f.limit ?? 50)),
    }));
  }

  async function showDetail(id: number) {
    try {
      const d = await obterAuditoria(id);
      setDetail(d);
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  const limit = filters.limit ?? 50;
  const offset = filters.offset ?? 0;

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog dialog-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Auditoria</h2>

        <form onSubmit={applyFilters} style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <select
            value={filters.acao ?? ""}
            onChange={(e) => setFilters({ ...filters, acao: e.target.value || undefined })}
          >
            <option value="">— ação —</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
          </select>
          <input
            placeholder="entidade contém…"
            value={filters.entidade ?? ""}
            onChange={(e) => setFilters({ ...filters, entidade: e.target.value || undefined })}
          />
          <input
            type="number"
            placeholder="user_id"
            value={filters.user_id ?? ""}
            onChange={(e) =>
              setFilters({
                ...filters,
                user_id: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            style={{ width: 90 }}
          />
          <label>
            de
            <input
              type="datetime-local"
              value={filters.from ?? ""}
              onChange={(e) => setFilters({ ...filters, from: e.target.value || undefined })}
            />
          </label>
          <label>
            até
            <input
              type="datetime-local"
              value={filters.to ?? ""}
              onChange={(e) => setFilters({ ...filters, to: e.target.value || undefined })}
            />
          </label>
          <button type="submit" className="primary">Filtrar</button>
        </form>

        {loading ? (
          <p>Carregando…</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Usuário</th>
                  <th>Ação</th>
                  <th>Entidade</th>
                  <th>ID</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} onClick={() => showDetail(it.id)} style={{ cursor: "pointer" }}>
                    <td>{new Date(it.criado_em).toLocaleString()}</td>
                    <td>{it.user_nome ?? <em>—</em>}</td>
                    <td>{it.acao}</td>
                    <td>{it.entidade}</td>
                    <td>{it.entidade_id ?? "—"}</td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <em>Sem registros.</em>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
              <span>
                {offset + 1}–{Math.min(offset + limit, total)} de {total}
              </span>
              <div>
                <button onClick={prevPage} disabled={offset === 0}>‹ Anterior</button>
                <button onClick={nextPage} disabled={offset + limit >= total}>Próxima ›</button>
              </div>
            </div>
          </>
        )}

        <div style={{ textAlign: "right", marginTop: 16 }}>
          <button onClick={onClose}>Fechar</button>
        </div>

        {detail && (
          <div className="dialog-backdrop" onClick={() => setDetail(null)} style={{ zIndex: 100 }}>
            <div className="dialog" onClick={(e) => e.stopPropagation()}>
              <h3>Detalhe — #{detail.id}</h3>
              <p>
                <strong>{detail.acao}</strong> {detail.entidade}{" "}
                {detail.entidade_id ? `(id=${detail.entidade_id})` : ""}
              </p>
              <p>
                {new Date(detail.criado_em).toLocaleString()} ·{" "}
                {detail.user_nome ?? <em>sem usuário</em>}
              </p>
              <pre style={{ background: "#f5f5f5", padding: 8, fontSize: 12, overflow: "auto", maxHeight: 320 }}>
                {JSON.stringify(detail.payload_jsonb, null, 2)}
              </pre>
              <div style={{ textAlign: "right" }}>
                <button onClick={() => setDetail(null)}>Fechar</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AdminDialog({
  onClose,
  currentUserId,
}: {
  onClose: () => void;
  currentUserId: number;
}) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newForm, setNewForm] = useState<UserCreate>({
    nome: "",
    email: "",
    password: "",
    role: "leitura",
  });
  const [busy, setBusy] = useState(false);

  function refresh() {
    setLoading(true);
    listarUsuarios()
      .then((u) => setUsers(u))
      .catch((e) => alert(`Erro: ${e}`))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (newForm.password.length < 8) {
      alert("Senha precisa ter no mínimo 8 caracteres");
      return;
    }
    setBusy(true);
    try {
      await criarUsuario(newForm);
      setNewForm({ nome: "", email: "", password: "", role: "leitura" });
      setShowNew(false);
      refresh();
    } catch (e) {
      alert(`Erro: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange(u: User, novoRole: string) {
    try {
      await atualizarUsuario(u.id, { role: novoRole as UserCreate["role"] });
      refresh();
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  async function handleToggleAtivo(u: User) {
    if (u.id === currentUserId && u.ativo) {
      alert("Não pode desativar a própria conta");
      return;
    }
    try {
      await atualizarUsuario(u.id, { ativo: !u.ativo });
      refresh();
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  async function handleResetSenha(u: User) {
    const senha = prompt(`Nova senha para ${u.email} (mín. 8 chars):`);
    if (!senha || senha.length < 8) return;
    try {
      await atualizarUsuario(u.id, { password: senha });
      alert("Senha atualizada");
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  async function handleDesativar(u: User) {
    if (u.id === currentUserId) {
      alert("Não pode desativar a própria conta");
      return;
    }
    if (!confirm(`Desativar ${u.email}?`)) return;
    try {
      await desativarUsuario(u.id);
      refresh();
    } catch (e) {
      alert(`Erro: ${e}`);
    }
  }

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog dialog-wide" onClick={(e) => e.stopPropagation()}>
        <h2>Usuários</h2>
        {loading ? (
          <p>Carregando…</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={u.ativo ? "" : "row-inactive"}>
                  <td>
                    {u.nome}
                    {u.id === currentUserId && <small> (você)</small>}
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u, e.target.value)}
                      disabled={u.id === currentUserId}
                    >
                      <option value="leitura">leitura</option>
                      <option value="escrevente">escrevente</option>
                      <option value="escrivao">escrivão</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td>{u.ativo ? "ativo" : "inativo"}</td>
                  <td>
                    <button onClick={() => handleToggleAtivo(u)}>
                      {u.ativo ? "Desativar" : "Reativar"}
                    </button>
                    <button onClick={() => handleResetSenha(u)}>Senha</button>
                    {!u.ativo && (
                      <button onClick={() => handleDesativar(u)} className="danger">
                        Excluir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={{ marginTop: 16 }}>
          {!showNew ? (
            <button onClick={() => setShowNew(true)} className="primary">
              + Novo usuário
            </button>
          ) : (
            <form onSubmit={handleCreate} className="new-user-form">
              <h3>Novo usuário</h3>
              <label>
                Nome
                <input
                  value={newForm.nome}
                  onChange={(e) => setNewForm({ ...newForm, nome: e.target.value })}
                  required
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={newForm.email}
                  onChange={(e) => setNewForm({ ...newForm, email: e.target.value })}
                  required
                />
              </label>
              <label>
                Senha (mín. 8)
                <input
                  type="password"
                  value={newForm.password}
                  onChange={(e) => setNewForm({ ...newForm, password: e.target.value })}
                  required
                  minLength={8}
                />
              </label>
              <label>
                Role
                <select
                  value={newForm.role}
                  onChange={(e) =>
                    setNewForm({ ...newForm, role: e.target.value as UserCreate["role"] })
                  }
                >
                  <option value="leitura">leitura</option>
                  <option value="escrevente">escrevente</option>
                  <option value="escrivao">escrivão</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <div style={{ marginTop: 8 }}>
                <button type="submit" disabled={busy} className="primary">
                  {busy ? "Criando…" : "Criar"}
                </button>
                <button type="button" onClick={() => setShowNew(false)}>
                  Cancelar
                </button>
              </div>
            </form>
          )}
        </div>

        <div style={{ textAlign: "right", marginTop: 16 }}>
          <button onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  );
}
