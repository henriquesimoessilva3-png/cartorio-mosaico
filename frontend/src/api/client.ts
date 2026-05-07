const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

const TOKEN_KEY = "cartorio-mosaico-token";

let _token: string | null = localStorage.getItem(TOKEN_KEY);

export function getToken(): string | null {
  return _token;
}

export function setToken(token: string | null): void {
  _token = token;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  return _token ? { Authorization: `Bearer ${_token}` } : {};
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
      ...(init.headers as Record<string, string> | undefined),
    },
  });
  if (r.status === 401) {
    setToken(null);
    throw new Error("Não autenticado (401)");
  }
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status}: ${text || r.statusText}`);
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

export interface TenantInfo {
  id: number;
  slug: string;
  nome: string;
}

export interface User {
  id: number;
  nome: string;
  email: string;
  role: string;
  ativo: boolean;
  tenant_id?: number | null;
  tenant?: TenantInfo | null;
}

export async function healthCheck(): Promise<{ status: string }> {
  return request("/health");
}

export async function login(
  email: string,
  password: string,
): Promise<{ token: string; user: User }> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!r.ok) throw new Error("Credenciais inválidas");
  const { access_token } = (await r.json()) as { access_token: string };
  setToken(access_token);
  const user = await me();
  return { token: access_token, user };
}

export async function me(): Promise<User> {
  return request("/api/auth/me");
}

export function logout(): void {
  setToken(null);
}

export interface Matricula {
  id: number;
  numero: string;
  proprietario_atual_nome: string | null;
  endereco_logradouro: string | null;
  status_geometria: string;
  area_descrita_texto: string | null;
  area_descrita_m2: number | null;
}

export interface MatriculaCreate {
  numero: string;
  proprietario_atual_nome?: string | null;
  endereco_logradouro?: string | null;
  area_descrita_texto?: string | null;
  cpf_cnpj?: string | null;
}

export async function listarMatriculas(): Promise<Matricula[]> {
  return request("/api/matriculas");
}

export async function criarMatricula(payload: MatriculaCreate): Promise<Matricula> {
  return request("/api/matriculas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface Lote {
  id: number;
  matricula_id: number;
  versao: number;
  area_calculada_m2: number | null;
  perimetro_m: number | null;
  vertices_jsonb: Array<{ marco: string; e_utm: number; n_utm: number; lat: number; lon: number }> | null;
  azimutes_jsonb: Array<Record<string, unknown>> | null;
  notas_validacao: string | null;
  hash_documento: string | null;
  criado_em: string;
}

export interface LoteCreate {
  matricula_id: number;
  vertices: [number, number][];
  notas_validacao?: string;
}

export async function criarLote(payload: LoteCreate): Promise<Lote> {
  return request("/api/lotes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function lotesPorMatricula(matriculaId: number): Promise<Lote[]> {
  return request(`/api/lotes/por-matricula/${matriculaId}`);
}

export interface ValidacaoTextual {
  numeros_extraidos: number[];
  matches: Array<{ valor_texto_m: number; lado_real_m: number; diff_pct: number }>;
  avisos: string[];
  confrontantes_textuais: Array<{ lado: string; descricao: string }>;
}

export async function validacaoTextual(loteId: number): Promise<ValidacaoTextual> {
  return request(`/api/lotes/${loteId}/validacao-textual`);
}

// Admin de usuários
export async function listarUsuarios(): Promise<User[]> {
  return request("/api/auth/users");
}

export interface UserCreate {
  nome: string;
  email: string;
  password: string;
  role: "admin" | "escrivao" | "escrevente" | "leitura";
}

export async function criarUsuario(payload: UserCreate): Promise<User> {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface UserUpdate {
  nome?: string;
  role?: "admin" | "escrivao" | "escrevente" | "leitura";
  ativo?: boolean;
  password?: string;
}

export async function atualizarUsuario(id: number, payload: UserUpdate): Promise<User> {
  return request(`/api/auth/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function desativarUsuario(id: number): Promise<void> {
  return request(`/api/auth/users/${id}`, { method: "DELETE" });
}

// Auditoria reversa (admin only)
export interface AuditoriaListItem {
  id: number;
  user_id: number | null;
  user_nome: string | null;
  acao: string;
  entidade: string;
  entidade_id: number | null;
  criado_em: string;
}

export interface AuditoriaDetail extends AuditoriaListItem {
  payload_jsonb: Record<string, unknown> | null;
}

export interface AuditoriaListResponse {
  items: AuditoriaListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditoriaFilters {
  limit?: number;
  offset?: number;
  user_id?: number;
  acao?: string;
  entidade?: string;
  from?: string;
  to?: string;
}

export async function listarAuditorias(
  params: AuditoriaFilters = {},
): Promise<AuditoriaListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request(`/api/auditorias${suffix}`);
}

export async function obterAuditoria(id: number): Promise<AuditoriaDetail> {
  return request(`/api/auditorias/${id}`);
}

export interface Conflito {
  lote_a: number;
  matricula_a: number;
  lote_b: number;
  matricula_b: number;
  area_overlap_m2: number;
}

export async function buscarMosaico(): Promise<GeoJSON.FeatureCollection> {
  return request("/api/mosaico");
}

export async function buscarConflitos(): Promise<{ overlaps: Conflito[] }> {
  return request("/api/mosaico/conflitos");
}

export interface PdfOptions {
  cartorio_nome?: string;
  cartorio_comarca?: string;
  operador_nome?: string;
  croqui_width?: number;
  croqui_height?: number;
  croqui_pad?: number;
  marker_size?: number;
  font_size?: number;
  page_margin_cm?: number;
  tile_zoom_override?: number;
  usar_satelite?: boolean;
}

function _serializeOpts(opts: PdfOptions = {}, extra: Record<string, string> = {}): string {
  const qs = new URLSearchParams(extra);
  Object.entries(opts).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function memorialPdfUrl(loteId: number, opts: PdfOptions = {}): string {
  // Token via query string permite download direto via <a href download>.
  const extra: Record<string, string> = {};
  if (_token) extra.token = _token;
  return `${BASE}/api/memoriais/${loteId}.pdf${_serializeOpts(opts, extra)}`;
}

export async function baixarMemorialPdf(
  loteId: number,
  opts: PdfOptions = {},
): Promise<Blob> {
  const r = await fetch(
    `${BASE}/api/memoriais/${loteId}.pdf${_serializeOpts(opts)}`,
    { headers: authHeaders() },
  );
  if (!r.ok) throw new Error(`PDF: ${r.status}`);
  return r.blob();
}

export async function previewCroquiBlob(
  loteId: number,
  opts: PdfOptions = {},
): Promise<Blob> {
  const r = await fetch(
    `${BASE}/api/memoriais/${loteId}.pdf${_serializeOpts({ ...opts }, { format: "preview" })}`,
    { headers: authHeaders() },
  );
  if (!r.ok) throw new Error(`Preview: ${r.status}`);
  return r.blob();
}
