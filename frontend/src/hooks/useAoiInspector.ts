/**
 * useAoiInspector — when an AOI polygon is drawn, compute area stats
 * from the loaded OSM GIS layers and return available analyses.
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
  bbox: [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
  buildings: number | null;   // count, null = data not loaded yet
  roadKm: number | null;      // road length in km
  waterwayKm: number | null;  // waterway length in km
  parks: number | null;       // count
}

export interface AvailableAnalysis {
  id: string;
  icon: string;
  title: string;
  description: string;
  category: 'hazard' | 'suitability' | 'infrastructure' | 'environment';
  available: boolean;
  note?: string;
}

export interface AoiInspection {
  stats: AoiStats;
  analyses: AvailableAnalysis[];
}

// ---------------------------------------------------------------------------
// Available analysis catalogue
// ---------------------------------------------------------------------------
const ANALYSIS_CATALOGUE: AvailableAnalysis[] = [
  {
    id: 'development-suitability',
    icon: '🏗️',
    title: 'Development Suitability',
    description: 'Multi-criteria land suitability for urban/residential development',
    category: 'suitability',
    available: true,
  },
  {
    id: 'agriculture-suitability',
    icon: '🌾',
    title: 'Agricultural Suitability',
    description: 'Soil, slope, and climate suitability for farming and crops',
    category: 'suitability',
    available: true,
  },
  {
    id: 'cyclone-risk',
    icon: '🌀',
    title: 'Cyclone Hazard Risk',
    description: 'Historical cyclone track exposure and wind speed zones',
    category: 'hazard',
    available: true,
  },
  {
    id: 'flood-risk',
    icon: '🌊',
    title: 'Flood Risk Assessment',
    description: 'River flood extent, coastal inundation and drainage analysis',
    category: 'hazard',
    available: true,
  },
  {
    id: 'tsunami-vulnerability',
    icon: '🌊',
    title: 'Tsunami Vulnerability',
    description: 'Coastal run-up zones and population exposure mapping',
    category: 'hazard',
    available: true,
  },
  {
    id: 'earthquake-hazard',
    icon: '📳',
    title: 'Earthquake Hazard',
    description: 'Seismic intensity, fault proximity and ground shaking potential',
    category: 'hazard',
    available: true,
  },
  {
    id: 'volcanic-hazard',
    icon: '🌋',
    title: 'Volcanic Hazard',
    description: 'Lava flow paths, ashfall extent and exclusion zone analysis',
    category: 'hazard',
    available: true,
  },
  {
    id: 'landslide-risk',
    icon: '🏔️',
    title: 'Landslide Risk',
    description: 'Slope stability, soil saturation and mass movement susceptibility',
    category: 'hazard',
    available: true,
  },
  {
    id: 'infrastructure-assessment',
    icon: '🛣️',
    title: 'Infrastructure Assessment',
    description: 'Road access, building density and utility coverage analysis',
    category: 'infrastructure',
    available: true,
  },
  {
    id: 'building-vulnerability',
    icon: '🏚️',
    title: 'Building Vulnerability',
    description: 'Structural exposure and damage probability for buildings',
    category: 'infrastructure',
    available: true,
  },
  {
    id: 'coastal-erosion',
    icon: '🏝️',
    title: 'Coastal Erosion',
    description: 'Shoreline change rates and coastal retreat modelling',
    category: 'environment',
    available: true,
  },
  {
    id: 'biodiversity',
    icon: '🦜',
    title: 'Biodiversity & Conservation',
    description: 'Habitat sensitivity, protected areas and ecological connectivity',
    category: 'environment',
    available: true,
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Rough perimeter in km for a polygon ring (haversine per segment) */
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
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
    total += R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return total;
}

/** Haversine distance in km between two [lng, lat] points */
function distKm(a: [number, number], b: [number, number]): number {
  const R = 6371;
  const dLat = ((b[1] - a[1]) * Math.PI) / 180;
  const dLng = ((b[0] - a[0]) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a[1] * Math.PI) / 180) * Math.cos((b[1] * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

/** Ray-casting point-in-polygon test */
function pointInPolygon(pt: [number, number], ring: [number, number][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/** Approximate length in km for a LineString feature intersecting the AOI bbox */
function lineStringLengthKm(coords: [number, number][]): number {
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    total += distKm(coords[i], coords[i + 1]);
  }
  return total;
}

// ---------------------------------------------------------------------------
// Main function: count features from MapLibre source that fall in the AOI
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
    // querySourceFeatures returns all tiles' features (not just visible ones)
    const features: MapGeoJSONFeature[] = (map as unknown as {
      querySourceFeatures(id: string): MapGeoJSONFeature[];
    }).querySourceFeatures(sourceId);

    for (const f of features) {
      if (!f.geometry) continue;

      if (f.geometry.type === 'Polygon') {
        // Check if centroid is in AOI
        const coords = (f.geometry as GeoJSON.Polygon).coordinates[0] as [number, number][];
        if (coords.length < 3) continue;
        const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length;
        const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length;
        if (cx >= bbox[0] && cx <= bbox[2] && cy >= bbox[1] && cy <= bbox[3]) {
          if (pointInPolygon([cx, cy], ring)) count++;
        }
      } else if (f.geometry.type === 'LineString') {
        const coords = (f.geometry as GeoJSON.LineString).coordinates as [number, number][];
        // Check if any vertex is in the AOI bbox
        const inBbox = coords.some(
          ([lng, lat]) => lng >= bbox[0] && lng <= bbox[2] && lat >= bbox[1] && lat <= bbox[3]
        );
        if (inBbox) {
          const inPoly = coords.some(c => pointInPolygon(c as [number, number], ring));
          if (inPoly) {
            lengthKm += lineStringLengthKm(coords);
            count++;
          }
        }
      } else if (f.geometry.type === 'Point') {
        const [lng, lat] = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        if (lng >= bbox[0] && lng <= bbox[2] && lat >= bbox[1] && lat <= bbox[3]) {
          if (pointInPolygon([lng, lat], ring)) count++;
        }
      }
    }
  } catch {
    // source may not be ready yet
  }

  return { count, lengthKm };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useAoiInspector(
  aoi: GeoJSON.Polygon | null,
  mapRef: RefObject<MapLibreMap | null>,
  osmLayersLoaded: boolean
): AoiInspection | null {
  const [inspection, setInspection] = useState<AoiInspection | null>(null);

  useEffect(() => {
    if (!aoi) {
      setInspection(null);
      return;
    }

    const polygon = { type: 'Feature', geometry: aoi, properties: {} } as GeoJSON.Feature<GeoJSON.Polygon>;
    const areaSqKm = turfArea(polygon) / 1_000_000;
    const bbox = turfBbox(polygon) as [number, number, number, number];
    const ring = aoi.coordinates[0] as [number, number][];
    const perimeterKm = ringPerimeterKm(ring);

    // Base stats (geometry only)
    const baseStats: AoiStats = {
      areaSqKm,
      perimeterKm,
      bbox,
      buildings: null,
      roadKm: null,
      waterwayKm: null,
      parks: null,
    };

    setInspection({ stats: baseStats, analyses: ANALYSIS_CATALOGUE });

    // Enrich with GIS layer counts once OSM data is available
    if (mapRef.current && osmLayersLoaded) {
      const m = mapRef.current;
      const buildings = countFeaturesInAoi(m, 'osm-buildings', aoi);
      const roads = countFeaturesInAoi(m, 'osm-roads', aoi);
      const waterways = countFeaturesInAoi(m, 'osm-waterways', aoi);
      const parks = countFeaturesInAoi(m, 'osm-parks', aoi);

      setInspection({
        stats: {
          ...baseStats,
          buildings: buildings.count,
          roadKm: Math.round(roads.lengthKm * 10) / 10,
          waterwayKm: Math.round(waterways.lengthKm * 10) / 10,
          parks: parks.count,
        },
        analyses: ANALYSIS_CATALOGUE,
      });
    }
  }, [aoi, osmLayersLoaded]);

  return inspection;
}
