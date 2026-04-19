/**
 * useAoiInspector — when an AOI polygon is drawn, compute area stats
 * from the loaded OSM GIS layers and return all 12 available analyses.
 */

import { useEffect, useState } from 'react';
import turfArea from '@turf/area';
import turfBbox from '@turf/bbox';
import type { Map as MapLibreMap, MapGeoJSONFeature } from 'maplibre-gl';
import type { RefObject } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AoiStats {
  areaSqKm: number;
  perimeterKm: number;
  bbox: [number, number, number, number];
  buildings: number | null;
  roadKm: number | null;
  waterwayKm: number | null;
  parks: number | null;
}

export interface AvailableAnalysis {
  id: string;
  icon: string;
  title: string;
  description: string;
  category: 'hazard' | 'suitability' | 'infrastructure' | 'environment';
  available: true;
  pending: false;
  note?: string;
}

export interface AoiInspection {
  stats: AoiStats;
  analyses: AvailableAnalysis[];
  osmLoading: boolean;
}

// ---------------------------------------------------------------------------
// All 12 analyses — always shown regardless of location or OSM features
// ---------------------------------------------------------------------------
const CATALOGUE: AvailableAnalysis[] = [
  { id: 'development-suitability',   icon: '🏗️', title: 'Development Suitability',    description: 'Multi-criteria land suitability for urban and residential development',    category: 'suitability',    available: true, pending: false },
  { id: 'agriculture-suitability',   icon: '🌾', title: 'Agricultural Suitability',   description: 'Soil, slope and climate suitability for farming and crops',                category: 'suitability',    available: true, pending: false },
  { id: 'cyclone-risk',              icon: '🌀', title: 'Cyclone Hazard Risk',         description: 'Historical cyclone track exposure and wind speed zones',                   category: 'hazard',         available: true, pending: false },
  { id: 'flood-risk',                icon: '🌊', title: 'Flood Risk Assessment',       description: 'River flood extent, coastal inundation and drainage analysis',             category: 'hazard',         available: true, pending: false },
  { id: 'tsunami-vulnerability',     icon: '🌊', title: 'Tsunami Vulnerability',       description: 'Coastal run-up zones and population exposure mapping',                     category: 'hazard',         available: true, pending: false },
  { id: 'earthquake-hazard',         icon: '📳', title: 'Earthquake Hazard',           description: 'Seismic intensity, fault proximity and ground shaking potential',          category: 'hazard',         available: true, pending: false },
  { id: 'volcanic-hazard',           icon: '🌋', title: 'Volcanic Hazard',             description: 'Lava flow paths, ashfall extent and exclusion zone analysis',              category: 'hazard',         available: true, pending: false },
  { id: 'landslide-risk',            icon: '🏔️', title: 'Landslide Risk',              description: 'Slope stability, soil saturation and mass movement susceptibility',        category: 'hazard',         available: true, pending: false },
  { id: 'infrastructure-assessment', icon: '🛣️', title: 'Infrastructure Assessment',   description: 'Road access, building density and utility coverage analysis',              category: 'infrastructure', available: true, pending: false },
  { id: 'building-vulnerability',    icon: '🏚️', title: 'Building Vulnerability',      description: 'Structural exposure and damage probability for existing buildings',        category: 'infrastructure', available: true, pending: false },
  { id: 'coastal-erosion',           icon: '🏝️', title: 'Coastal Erosion',             description: 'Shoreline change rates and coastal retreat modelling',                     category: 'environment',    available: true, pending: false },
  { id: 'biodiversity',              icon: '🦜', title: 'Biodiversity & Conservation', description: 'Habitat sensitivity, protected areas and ecological connectivity',         category: 'environment',    available: true, pending: false },
];

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------
function ringPerimeterKm(coords: [number, number][]): number {
  const R = 6371;
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const [lng1, lat1] = coords[i];
    const [lng2, lat2] = coords[i + 1];
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
    total += R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return total;
}

function distKm(a: [number, number], b: [number, number]): number {
  const R = 6371;
  const dLat = ((b[1] - a[1]) * Math.PI) / 180;
  const dLng = ((b[0] - a[0]) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a[1] * Math.PI) / 180) * Math.cos((b[1] * Math.PI) / 180) *
    Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

function pointInPolygon(pt: [number, number], ring: [number, number][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}

function lineStringLengthKm(coords: [number, number][]): number {
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++)
    total += distKm(coords[i], coords[i + 1]);
  return total;
}

// ---------------------------------------------------------------------------
// OSM feature counting
// ---------------------------------------------------------------------------
function countFeaturesInAoi(
  map: MapLibreMap,
  sourceId: string,
  aoi: GeoJSON.Polygon
): { count: number; lengthKm: number } {
  const ring = aoi.coordinates[0] as [number, number][];
  const bbox = turfBbox({ type: 'Feature', geometry: aoi, properties: {} });
  let count = 0;
  let lengthKm = 0;

  try {
    const features: MapGeoJSONFeature[] = (map as unknown as {
      querySourceFeatures(id: string): MapGeoJSONFeature[];
    }).querySourceFeatures(sourceId);

    for (const f of features) {
      if (!f.geometry) continue;

      if (f.geometry.type === 'Polygon') {
        const coords = (f.geometry as GeoJSON.Polygon).coordinates[0] as [number, number][];
        if (coords.length < 3) continue;
        const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length;
        const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length;
        if (cx >= bbox[0] && cx <= bbox[2] && cy >= bbox[1] && cy <= bbox[3])
          if (pointInPolygon([cx, cy], ring)) count++;
      } else if (f.geometry.type === 'LineString') {
        const coords = (f.geometry as GeoJSON.LineString).coordinates as [number, number][];
        const inBbox = coords.some(
          ([lng, lat]) => lng >= bbox[0] && lng <= bbox[2] && lat >= bbox[1] && lat <= bbox[3]
        );
        if (inBbox && coords.some(c => pointInPolygon(c as [number, number], ring))) {
          lengthKm += lineStringLengthKm(coords);
          count++;
        }
      } else if (f.geometry.type === 'Point') {
        const [lng, lat] = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        if (lng >= bbox[0] && lng <= bbox[2] && lat >= bbox[1] && lat <= bbox[3])
          if (pointInPolygon([lng, lat], ring)) count++;
      }
    }
  } catch { /* source may not be ready */ }

  return { count, lengthKm };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useAoiInspector(
  aoi: GeoJSON.Polygon | null,
  mapRef: RefObject<MapLibreMap | null>,
  osmLayersLoaded: boolean,
): AoiInspection | null {
  const [inspection, setInspection] = useState<AoiInspection | null>(null);

  useEffect(() => {
    if (!aoi) { setInspection(null); return; }

    const polygon = { type: 'Feature', geometry: aoi, properties: {} } as GeoJSON.Feature<GeoJSON.Polygon>;
    const areaSqKm   = turfArea(polygon) / 1_000_000;
    const bbox       = turfBbox(polygon) as [number, number, number, number];
    const ring       = aoi.coordinates[0] as [number, number][];
    const perimeterKm = ringPerimeterKm(ring);

    // Show all 12 analyses immediately with geometry stats
    setInspection({
      stats: { areaSqKm, perimeterKm, bbox, buildings: null, roadKm: null, waterwayKm: null, parks: null },
      analyses: CATALOGUE,
      osmLoading: true,
    });

    // Enrich OSM counts once layers are ready
    if (mapRef.current && osmLayersLoaded) {
      const m = mapRef.current;
      const bldg  = countFeaturesInAoi(m, 'osm-buildings',  aoi);
      const road  = countFeaturesInAoi(m, 'osm-roads',      aoi);
      const water = countFeaturesInAoi(m, 'osm-waterways',  aoi);
      const park  = countFeaturesInAoi(m, 'osm-parks',      aoi);

      setInspection({
        stats: {
          areaSqKm,
          perimeterKm,
          bbox,
          buildings:  bldg.count,
          roadKm:     Math.round(road.lengthKm  * 10) / 10,
          waterwayKm: Math.round(water.lengthKm * 10) / 10,
          parks:      park.count,
        },
        analyses: CATALOGUE,
        osmLoading: false,
      });
    }
  }, [aoi, osmLayersLoaded]);

  return inspection;
}
