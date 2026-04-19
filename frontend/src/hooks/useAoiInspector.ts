/**
 * useAoiInspector — when an AOI polygon is drawn, compute area stats
 * from the loaded OSM GIS layers and return ONLY the analyses that can
 * actually be generated for that specific location and its observable features.
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
  /** True while OSM data is still loading — availability not yet determined */
  pending: boolean;
  note?: string;
}

export interface AoiInspection {
  stats: AoiStats;
  /** Only analyses that can genuinely be generated — unavailable ones are excluded */
  analyses: AvailableAnalysis[];
  osmLoading: boolean;
}

// ---------------------------------------------------------------------------
// Vanuatu geography constants
// ---------------------------------------------------------------------------

/** Known active / frequently erupting volcanoes [lng, lat] */
const ACTIVE_VOLCANOES: [number, number][] = [
  [169.447, -19.532],  // Yasur, Tanna — permanently active
  [167.500, -14.270],  // Gaua, Banks Islands
  [167.833, -15.383],  // Ambae (Aoba)
  [168.120, -16.250],  // Ambrym — twin-caldera, very active
  [168.348, -16.508],  // Lopevi
  [168.167, -17.017],  // Epi (Tavani Ruro)
];

/** Volcanic hazard zone radius km — includes ash fall, seismic amplification, lava flow */
const VOLCANO_RADIUS_KM = 130;

// ---------------------------------------------------------------------------
// Full catalogue — availability is computed at runtime, not hardcoded
// ---------------------------------------------------------------------------
interface CatalogueEntry {
  id: string;
  icon: string;
  title: string;
  description: string;
  category: AvailableAnalysis['category'];
  /** 'always' | 'volcano' | 'coastal' | 'has-buildings' | 'has-roads' | 'has-waterways' */
  requires: string[];
}

const CATALOGUE: CatalogueEntry[] = [
  // Suitability — always available: the engine scores every point in Vanuatu
  {
    id: 'development-suitability',
    icon: '🏗️',
    title: 'Development Suitability',
    description: 'Multi-criteria land suitability for urban and residential development',
    category: 'suitability',
    requires: [],
  },
  {
    id: 'agriculture-suitability',
    icon: '🌾',
    title: 'Agricultural Suitability',
    description: 'Soil, slope and climate suitability for farming and crops',
    category: 'suitability',
    requires: [],
  },
  // Hazards always present in Vanuatu
  {
    id: 'cyclone-risk',
    icon: '🌀',
    title: 'Cyclone Hazard Risk',
    description: 'Historical cyclone track exposure and wind speed zones',
    category: 'hazard',
    requires: [],
  },
  {
    id: 'flood-risk',
    icon: '🌊',
    title: 'Flood Risk Assessment',
    description: 'River flood extent, coastal inundation and drainage analysis',
    category: 'hazard',
    requires: [],
  },
  {
    id: 'earthquake-hazard',
    icon: '📳',
    title: 'Earthquake Hazard',
    description: 'Seismic intensity, fault proximity and ground shaking potential',
    category: 'hazard',
    requires: [],
  },
  {
    id: 'landslide-risk',
    icon: '🏔️',
    title: 'Landslide Risk',
    description: 'Slope stability, soil saturation and mass movement susceptibility',
    category: 'hazard',
    requires: [],
  },
  // Volcanic — only near active volcanoes
  {
    id: 'volcanic-hazard',
    icon: '🌋',
    title: 'Volcanic Hazard',
    description: 'Lava flow paths, ashfall extent and exclusion zone analysis',
    category: 'hazard',
    requires: ['volcano'],
  },
  // Coastal — only for areas near the coastline
  {
    id: 'tsunami-vulnerability',
    icon: '🌊',
    title: 'Tsunami Vulnerability',
    description: 'Coastal run-up zones and population exposure mapping',
    category: 'hazard',
    requires: ['coastal'],
  },
  {
    id: 'coastal-erosion',
    icon: '🏝️',
    title: 'Coastal Erosion',
    description: 'Shoreline change rates and coastal retreat modelling',
    category: 'environment',
    requires: ['coastal'],
  },
  // Infrastructure — only if OSM shows roads or buildings
  {
    id: 'infrastructure-assessment',
    icon: '🛣️',
    title: 'Infrastructure Assessment',
    description: 'Road access, building density and utility coverage analysis',
    category: 'infrastructure',
    requires: ['has-roads-or-buildings'],
  },
  {
    id: 'building-vulnerability',
    icon: '🏚️',
    title: 'Building Vulnerability',
    description: 'Structural exposure and damage probability for existing buildings',
    category: 'infrastructure',
    requires: ['has-buildings'],
  },
  // Environment — always available in Vanuatu
  {
    id: 'biodiversity',
    icon: '🦜',
    title: 'Biodiversity & Conservation',
    description: 'Habitat sensitivity, protected areas and ecological connectivity',
    category: 'environment',
    requires: [],
  },
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
// Geographic context evaluators
// ---------------------------------------------------------------------------

/**
 * True if the AOI center is within VOLCANO_RADIUS_KM of any active volcano.
 */
function checkNearVolcano(center: [number, number]): boolean {
  return ACTIVE_VOLCANOES.some(v => distKm(center, v) < VOLCANO_RADIUS_KM);
}

/**
 * True if the AOI is in a coastal zone.
 *
 * All Vanuatu land is on islands. The only significantly "inland" zone
 * is the deep interior of Espiritu Santo (roughly 166.75–167.15 °E,
 * 14.6–16.0 °S) where some points are >20 km from the coast.
 * Everywhere else in the archipelago is within 15 km of saltwater.
 */
function checkIsCoastal(center: [number, number], bbox: [number, number, number, number]): boolean {
  const [lng, lat] = center;

  // Santo interior exclusion zone
  const inSantoInterior =
    lng >= 166.75 && lng <= 167.15 &&
    lat >= -16.0  && lat <= -14.6;

  if (inSantoInterior) {
    // The AOI may still touch the coast — check if the bbox is wide enough
    // to span the interior (i.e. straddles a coastline)
    const bboxWidthKm = distKm([bbox[0], lat], [bbox[2], lat]);
    if (bboxWidthKm > 15) return true; // large AOI likely spans to coast
    return false;
  }

  return true; // everywhere else in Vanuatu is coastal
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
  } catch { /* source not ready */ }

  return { count, lengthKm };
}

// ---------------------------------------------------------------------------
// Availability evaluator
// ---------------------------------------------------------------------------
interface OsmCounts {
  buildings: number | null;
  roadKm: number | null;
  waterwayKm: number | null;
  parks: number | null;
}

function evaluateAvailability(
  entry: CatalogueEntry,
  geo: { nearVolcano: boolean; coastal: boolean },
  osm: OsmCounts,
  osmLoaded: boolean,
): AvailableAnalysis | null {
  let available = true;
  let pending = false;
  let note: string | undefined;

  for (const req of entry.requires) {
    switch (req) {
      case 'volcano':
        if (!geo.nearVolcano) return null; // hide entirely
        break;

      case 'coastal':
        if (!geo.coastal) return null; // hide entirely
        break;

      case 'has-buildings':
        if (!osmLoaded) {
          pending = true; // we don't know yet — show as loading
        } else if ((osm.buildings ?? 0) === 0) {
          return null; // no buildings → hide entirely
        }
        break;

      case 'has-roads-or-buildings':
        if (!osmLoaded) {
          pending = true;
        } else if ((osm.roadKm ?? 0) === 0 && (osm.buildings ?? 0) === 0) {
          return null;
        }
        break;

      case 'has-waterways':
        if (!osmLoaded) {
          pending = true;
        } else if ((osm.waterwayKm ?? 0) === 0) {
          return null;
        }
        break;
    }
  }

  if (!available) return null;

  return {
    id:          entry.id,
    icon:        entry.icon,
    title:       entry.title,
    description: entry.description,
    category:    entry.category,
    available,
    pending,
    note,
  };
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
    const areaSqKm = turfArea(polygon) / 1_000_000;
    const bbox = turfBbox(polygon) as [number, number, number, number];
    const ring = aoi.coordinates[0] as [number, number][];
    const perimeterKm = ringPerimeterKm(ring);

    // AOI centre point
    const center: [number, number] = [
      (bbox[0] + bbox[2]) / 2,
      (bbox[1] + bbox[3]) / 2,
    ];

    // Geographic context (instant, no data loading needed)
    const geo = {
      nearVolcano: checkNearVolcano(center),
      coastal:     checkIsCoastal(center, bbox),
    };

    // Base OSM counts (unknown until layers load)
    const baseOsm: OsmCounts = { buildings: null, roadKm: null, waterwayKm: null, parks: null };

    function buildInspection(osm: OsmCounts, osmLoaded: boolean): AoiInspection {
      const analyses = CATALOGUE
        .map(e => evaluateAvailability(e, geo, osm, osmLoaded))
        .filter((a): a is AvailableAnalysis => a !== null);

      return {
        stats: {
          areaSqKm,
          perimeterKm,
          bbox,
          buildings:   osm.buildings,
          roadKm:      osm.roadKm,
          waterwayKm:  osm.waterwayKm,
          parks:       osm.parks,
        },
        analyses,
        osmLoading: !osmLoaded,
      };
    }

    // Immediate render with geographic-only filtering
    setInspection(buildInspection(baseOsm, false));

    // Enrich once OSM data is ready
    if (mapRef.current && osmLayersLoaded) {
      const m = mapRef.current;
      const bldg = countFeaturesInAoi(m, 'osm-buildings', aoi);
      const road = countFeaturesInAoi(m, 'osm-roads', aoi);
      const water = countFeaturesInAoi(m, 'osm-waterways', aoi);
      const park = countFeaturesInAoi(m, 'osm-parks', aoi);

      const enriched: OsmCounts = {
        buildings:  bldg.count,
        roadKm:     Math.round(road.lengthKm * 10) / 10,
        waterwayKm: Math.round(water.lengthKm * 10) / 10,
        parks:      park.count,
      };

      setInspection(buildInspection(enriched, true));
    }
  }, [aoi, osmLayersLoaded]);

  return inspection;
}
