import * as turf from "@turf/turf";
import proj4 from "proj4";

proj4.defs("EPSG:4674", "+proj=longlat +ellps=GRS80 +no_defs +type=crs");
proj4.defs(
  "EPSG:31983",
  "+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +type=crs",
);

export type LonLat = [number, number];

export function lonLatToUTM(lonLat: LonLat): [number, number] {
  return proj4("EPSG:4674", "EPSG:31983", lonLat) as [number, number];
}

export function decimalToDms(dec: number): string {
  const sign = dec < 0 ? "-" : "";
  const v = Math.abs(dec);
  const d = Math.floor(v);
  const mF = (v - d) * 60;
  const m = Math.floor(mF);
  const s = ((mF - m) * 60).toFixed(0).padStart(2, "0");
  return `${sign}${d}°${String(m).padStart(2, "0")}'${s}"`;
}

export interface Side {
  from: number;
  to: number;
  distM: number;
  azDms: string;
  azDeg: number;
}

export function computeSides(vertices: LonLat[]): Side[] {
  const sides: Side[] = [];
  for (let i = 0; i < vertices.length; i++) {
    const a = vertices[i];
    const b = vertices[(i + 1) % vertices.length];
    const aUTM = lonLatToUTM(a);
    const bUTM = lonLatToUTM(b);
    const dE = bUTM[0] - aUTM[0];
    const dN = bUTM[1] - aUTM[1];
    const distM = Math.hypot(dE, dN);
    let azDeg = (Math.atan2(dE, dN) * 180) / Math.PI;
    if (azDeg < 0) azDeg += 360;
    sides.push({
      from: i,
      to: (i + 1) % vertices.length,
      distM,
      azDms: decimalToDms(azDeg),
      azDeg,
    });
  }
  return sides;
}

export function computeArea(vertices: LonLat[]): number {
  if (vertices.length < 3) return 0;
  const ring = [...vertices, vertices[0]];
  return turf.area(turf.polygon([ring]));
}

export function computePerimeter(vertices: LonLat[]): number {
  if (vertices.length < 2) return 0;
  let p = 0;
  for (let i = 0; i < vertices.length; i++) {
    const a = vertices[i];
    const b = vertices[(i + 1) % vertices.length];
    const aUTM = lonLatToUTM(a);
    const bUTM = lonLatToUTM(b);
    p += Math.hypot(bUTM[0] - aUTM[0], bUTM[1] - aUTM[1]);
  }
  return p;
}
