/**
 * useOSMLayers — fetches Vanuatu OSM feature layers from the Overpass API
 * and adds them to a MapLibre map instance.
 *
 * Uses `out geom;` so geometry is embedded in each element — no separate
 * node-lookup step needed.
 */

import { useEffect, useState, useRef } from 'react';
import type { Map as MapLibreMap } from 'maplibre-gl';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type LayerStatus = 'idle' | 'loading' | 'loaded' | 'error';

export interface OSMLayerState {
  buildings: LayerStatus;
  roads: LayerStatus;
  waterways: LayerStatus;
  parks: LayerStatus;
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const OVERPASS_ENDPOINT = 'https://overpass.openstreetmap.fr/api/interpreter';

// Vanuatu bounding box: south,west,north,east
const BBOX = '-20.5,166.5,-13.0,170.5';

// Base path for static pre-fetched GeoJSON assets
const STATIC_BASE = '/vmhlss/data';

const LAYERS: Array<{
  key: keyof OSMLayerState;
  staticUrl?: string;   // served from GitHub Pages — fast
  query?: string;       // Overpass API fallback (for buildings, live fetch)
  sourceId: string;
  layers: MapLibreLayerDef[];
}> = [
  // ── Buildings — live Overpass fetch ────────────────────────────────────
  {
    key: 'buildings',
    sourceId: 'osm-buildings',
    query: `[out:json][timeout:60][maxsize:67108864];
(way["building"](${BBOX}););
out geom;`,
    layers: [
      {
        id: 'buildings-fill',
        type: 'fill',
        paint: {
          'fill-color': '#d4956a',
          'fill-opacity': 0.6,
        },
      },
      {
        id: 'buildings-outline',
        type: 'line',
        paint: {
          'line-color': '#a0623e',
          'line-width': 0.8,
        },
      },
    ],
  },

  // ── Roads — pre-fetched static file ────────────────────────────────────
  {
    key: 'roads',
    sourceId: 'osm-roads',
    staticUrl: `${STATIC_BASE}/roads.geojson`,
    layers: [
      {
        id: 'roads-casing',
        type: 'line',
        filter: ['in', ['get', 'highway'], ['literal', ['primary', 'secondary', 'trunk', 'motorway']]],
        paint: {
          'line-color': '#ffffff',
          'line-width': ['interpolate', ['linear'], ['zoom'], 8, 2, 14, 6],
          'line-gap-width': ['interpolate', ['linear'], ['zoom'], 8, 1, 14, 4],
        },
      },
      {
        id: 'roads-fill',
        type: 'line',
        paint: {
          'line-color': [
            'match', ['get', 'highway'],
            ['motorway', 'trunk'], '#e8912d',
            ['primary'], '#fcd44f',
            ['secondary'], '#ffffff',
            ['tertiary'], '#dddddd',
            ['residential', 'unclassified', 'living_street'], '#cccccc',
            ['track', 'path', 'footway'], '#b8a88a',
            '#aaaaaa',
          ],
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            8, ['match', ['get', 'highway'], ['motorway', 'trunk', 'primary'], 2, 0.5],
            14, ['match', ['get', 'highway'], ['motorway', 'trunk', 'primary'], 8, ['secondary', 'tertiary'], 5, 2],
          ],
        },
      },
    ],
  },

  // ── Waterways — pre-fetched static file ────────────────────────────────
  {
    key: 'waterways',
    sourceId: 'osm-waterways',
    staticUrl: `${STATIC_BASE}/waterways.geojson`,
    layers: [
      {
        id: 'waterways-line',
        type: 'line',
        paint: {
          'line-color': [
            'match', ['get', 'waterway'],
            'river', '#4a90d9',
            'canal', '#5ba3e0',
            '#82b4d8',
          ],
          'line-width': [
            'interpolate', ['linear'], ['zoom'],
            8, ['match', ['get', 'waterway'], 'river', 2, 0.8],
            14, ['match', ['get', 'waterway'], 'river', 5, 2],
          ],
          'line-opacity': 0.9,
        },
      },
    ],
  },

  // ── Parks — pre-fetched static file ────────────────────────────────────
  {
    key: 'parks',
    sourceId: 'osm-parks',
    staticUrl: `${STATIC_BASE}/parks.geojson`,
    layers: [
      {
        id: 'parks-fill',
        type: 'fill',
        paint: {
          'fill-color': [
            'match', ['get', 'leisure'],
            'nature_reserve', '#6ab04c',
            'park', '#55a630',
            '#80b94a',
          ],
          'fill-opacity': 0.4,
        },
      },
      {
        id: 'parks-outline',
        type: 'line',
        paint: {
          'line-color': '#3d7a22',
          'line-width': 1,
          'line-opacity': 0.7,
        },
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
interface MapLibreLayerDef {
  id: string;
  type: string;
  filter?: unknown[];
  paint: Record<string, unknown>;
}

interface OverpassElement {
  type: string;
  id: number;
  tags?: Record<string, string>;
  geometry?: Array<{ lat: number; lon: number }>;
  nodes?: number[];
}

/** Convert Overpass JSON (with `out geom`) to GeoJSON FeatureCollection */
function overpassToGeoJSON(data: { elements: OverpassElement[] }) {
  const features: GeoJSON.Feature[] = [];

  for (const el of data.elements) {
    if (el.type !== 'way' || !el.geometry) continue;

    const coords: [number, number][] = el.geometry.map(pt => [
      Math.round(pt.lon * 100000) / 100000,
      Math.round(pt.lat * 100000) / 100000,
    ]);

    if (coords.length < 2) continue;

    const isClosed =
      coords[0][0] === coords[coords.length - 1][0] &&
      coords[0][1] === coords[coords.length - 1][1] &&
      coords.length >= 4;

    const tags = el.tags || {};
    // Keep only the most useful properties
    const props: Record<string, string> = {};
    ['building', 'highway', 'waterway', 'leisure', 'landuse', 'name', 'boundary', 'natural'].forEach(
      k => { if (tags[k]) props[k] = tags[k]; }
    );

    features.push({
      type: 'Feature',
      id: el.id,
      properties: props,
      geometry: isClosed
        ? { type: 'Polygon', coordinates: [coords] }
        : { type: 'LineString', coordinates: coords },
    });
  }

  return { type: 'FeatureCollection' as const, features };
}

/** Fetch a static pre-built GeoJSON file */
async function fetchStatic(url: string): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Fetch one Overpass layer and return GeoJSON */
async function fetchOverpass(query: string): Promise<GeoJSON.FeatureCollection> {
  const body = new URLSearchParams({ data: query });
  const res = await fetch(OVERPASS_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (!json.elements) throw new Error('No elements in response');
  return overpassToGeoJSON(json);
}

/** Add a GeoJSON source + layers to the map */
function addToMap(
  map: MapLibreMap,
  sourceId: string,
  geojson: GeoJSON.FeatureCollection,
  layerDefs: MapLibreLayerDef[]
) {
  // Remove old source/layers if they exist (e.g. style reload)
  layerDefs.forEach(l => { if (map.getLayer(l.id)) map.removeLayer(l.id); });
  if (map.getSource(sourceId)) map.removeSource(sourceId);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  map.addSource(sourceId, { type: 'geojson', data: geojson as any });

  layerDefs.forEach(def => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const spec: any = {
      id: def.id,
      type: def.type,
      source: sourceId,
      paint: def.paint,
    };
    if (def.filter) spec.filter = def.filter;
    map.addLayer(spec);
  });
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useOSMLayers(map: MapLibreMap | null, mapLoaded: boolean) {
  const [status, setStatus] = useState<OSMLayerState>({
    buildings: 'idle',
    roads: 'idle',
    waterways: 'idle',
    parks: 'idle',
  });
  const fetchedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!map || !mapLoaded) return;

    // Use sessionStorage to cache GeoJSON per layer
    const loadLayer = async (layerCfg: typeof LAYERS[0]) => {
      const { key, sourceId, layers } = layerCfg;
      if (fetchedRef.current.has(key)) return;
      fetchedRef.current.add(key);

      setStatus(s => ({ ...s, [key]: 'loading' }));

      try {
        let geojson: GeoJSON.FeatureCollection;

        if (layerCfg.staticUrl) {
          // Static pre-fetched file — served from GitHub Pages CDN, no caching needed
          geojson = await fetchStatic(layerCfg.staticUrl);
        } else if (layerCfg.query) {
          // Live Overpass fetch — cache in sessionStorage
          const cached = sessionStorage.getItem(`osm-${key}`);
          if (cached) {
            geojson = JSON.parse(cached);
          } else {
            geojson = await fetchOverpass(layerCfg.query);
            try { sessionStorage.setItem(`osm-${key}`, JSON.stringify(geojson)); } catch { /* storage full */ }
          }
        } else {
          throw new Error('No source defined for layer');
        }

        if (map.loaded()) {
          addToMap(map, sourceId, geojson, layers);
        } else {
          map.once('load', () => addToMap(map, sourceId, geojson, layers));
        }
        setStatus(s => ({ ...s, [key]: 'loaded' }));
      } catch (err) {
        console.warn(`OSM layer ${key} failed:`, err);
        setStatus(s => ({ ...s, [key]: 'error' }));
        fetchedRef.current.delete(key);
      }
    };

    // Load layers sequentially to avoid hammering Overpass
    (async () => {
      for (const layer of LAYERS) {
        await loadLayer(layer);
        await new Promise(r => setTimeout(r, 500));
      }
    })();
  }, [map, mapLoaded]);

  return status;
}
