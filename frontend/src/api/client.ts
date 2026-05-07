const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export async function healthCheck(): Promise<{ status: string }> {
  const r = await fetch(`${BASE}/health`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
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

export async function listarMatriculas(): Promise<Matricula[]> {
  const r = await fetch(`${BASE}/api/matriculas`);
  if (!r.ok) throw new Error(`Listar matrículas: ${r.status}`);
  return r.json();
}

export async function criarMatricula(
  payload: Partial<Matricula> & { numero: string },
): Promise<Matricula> {
  const r = await fetch(`${BASE}/api/matriculas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Criar matrícula: ${r.status}`);
  return r.json();
}

export interface LoteCreate {
  matricula_id: number;
  vertices: [number, number][];
  notas_validacao?: string;
}

export async function criarLote(payload: LoteCreate) {
  const r = await fetch(`${BASE}/api/lotes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Criar lote: ${r.status}`);
  return r.json();
}

export function memorialPdfUrl(loteId: number): string {
  return `${BASE}/api/memoriais/${loteId}.pdf`;
}

export async function buscarMosaico(): Promise<GeoJSON.FeatureCollection> {
  const r = await fetch(`${BASE}/api/mosaico`);
  if (!r.ok) throw new Error(`Mosaico: ${r.status}`);
  return r.json();
}
