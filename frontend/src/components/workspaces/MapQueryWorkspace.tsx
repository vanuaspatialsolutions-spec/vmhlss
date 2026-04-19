import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import maplibregl, { Map as MapLibreMap, LngLatBounds, LngLatLike, MapMouseEvent } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useAuthStore, useAnalysisStore, useMapStore, useUIStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import { useOSMLayers } from '../../hooks/useOSMLayers';
import { useAoiInspector } from '../../hooks/useAoiInspector';
import MapLayerPanel from '../map/MapLayerPanel';
import QueryPanel from '../map/QueryPanel';
import ResultsPopup from '../map/ResultsPopup';
import AoiInspectorPanel from '../map/AoiInspectorPanel';
import type { GeoJSON } from '../../types/index';

export default function MapQueryWorkspace() {
  const navigate = useNavigate();
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [drawMode, setDrawMode] = useState<'polygon' | 'rectangle' | null>(null);
  const [selectedCoords, setSelectedCoords] = useState<[number, number][]>([]);
  const [popupContent, setPopupContent] = useState<any>(null);
  const [popupPosition, setPopupPosition] = useState<[number, number] | null>(null);

  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const {
    currentAoi,
    currentAnalysis,
    assessmentType,
    personasRequested,
    isProcessing,
    setAoi,
    setAnalysis,
    setIsProcessing,
  } = useAnalysisStore();
  const { mapCenter, mapZoom, baseMap, setMapCenter, setMapZoom, setBaseMap } = useMapStore();
  const { mapLayerPanelOpen, queryPanelOpen } = useUIStore();

  // OSM layers — pass the ref object (not map.current) so the hook reads the current value
  // when mapLoaded triggers, rather than the null value captured at render time
  const osmStatus = useOSMLayers(map, mapLoaded);

  // AOI Inspector — fires automatically when a polygon is drawn
  const osmAllLoaded = Object.values(osmStatus).every(s => s === 'loaded' || s === 'error');
  const aoiInspection = useAoiInspector(currentAoi, map, osmAllLoaded);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: getMapStyle(baseMap),
      center: mapCenter as [number, number],
      zoom: mapZoom,
      pitch: 0,
      bearing: 0,
    });

    // Force resize after mount so MapLibre picks up the correct canvas dimensions
    setTimeout(() => { map.current?.resize(); }, 100);

    map.current.on('error', (e) => {
      console.warn('MapLibre error:', e);
    });

    map.current.on('move', () => {
      if (map.current) {
        setMapCenter([map.current.getCenter().lng, map.current.getCenter().lat]);
        setMapZoom(map.current.getZoom());
      }
    });

    // Mark map as loaded — triggers OSM layer fetching
    map.current.on('load', () => {
      if (!map.current) return;
      setMapLoaded(true);
      addHazardLayers(map.current);
      addSuitabilityLayers(map.current);
    });

    return () => {
      map.current?.remove();
    };
  }, []);

  // Update map style when basemap changes
  useEffect(() => {
    if (map.current) {
      map.current.setStyle(getMapStyle(baseMap));
    }
  }, [baseMap]);

  // Draw AOI on map
  useEffect(() => {
    if (!map.current || !currentAoi) return;

    // Remove existing AOI layer
    if (map.current.getSource('aoi')) {
      map.current.removeLayer('aoi-fill');
      map.current.removeLayer('aoi-outline');
      map.current.removeSource('aoi');
    }

    // Add AOI
    map.current.addSource('aoi', {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: currentAoi,
        properties: {},
      },
    });

    map.current.addLayer({
      id: 'aoi-fill',
      type: 'fill',
      source: 'aoi',
      paint: {
        'fill-color': '#10b981',
        'fill-opacity': 0.2,
      },
    });

    map.current.addLayer({
      id: 'aoi-outline',
      type: 'line',
      source: 'aoi',
      paint: {
        'line-color': '#059669',
        'line-width': 2,
      },
    });

    // Fit bounds
    const coords = currentAoi.coordinates[0] as [number, number][];
    const bounds = coords.reduce(
      (b: LngLatBounds, coord) => b.extend(coord as LngLatLike),
      new LngLatBounds(coords[0] as LngLatLike, coords[0] as LngLatLike)
    );
    map.current.fitBounds(bounds, { padding: 50 });
  }, [currentAoi]);

  // Display results on map — triggered when analysis completes
  useEffect(() => {
    if (!map.current || !mapLoaded || !currentAnalysis?.results?.length) return;

    const m = map.current;

    // Remove any previous results layers
    ['results-halo', 'results-fill', 'results-label'].forEach(id => {
      if (m.getLayer(id)) m.removeLayer(id);
    });
    if (m.getSource('results')) m.removeSource('results');

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: currentAnalysis.results.map((result) => ({
        type: 'Feature' as const,
        geometry: result.geometry,
        properties: {
          suitabilityClass: result.suitabilityClass,
          chiScore: result.chiScore,
          confidence: result.confidence,
          label: result.suitabilityClass,
        },
      })),
    };

    m.addSource('results', { type: 'geojson', data: geojson as unknown as object });

    // White halo for visibility over basemap
    m.addLayer({
      id: 'results-halo',
      type: 'circle',
      source: 'results',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 10, 14, 18],
        'circle-color': '#ffffff',
        'circle-opacity': 0.5,
      },
    });

    // Coloured fill by suitability class
    m.addLayer({
      id: 'results-fill',
      type: 'circle',
      source: 'results',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 7, 14, 14],
        'circle-color': [
          'match', ['get', 'suitabilityClass'],
          'S1', '#166534',
          'S2', '#16a34a',
          'S3', '#ca8a04',
          'S4', '#ea580c',
          'S5', '#991b1b',
          '#6b7280',
        ],
        'circle-opacity': 0.9,
        'circle-stroke-width': 1.5,
        'circle-stroke-color': '#ffffff',
      },
    });

    // Class label at higher zoom
    m.addLayer({
      id: 'results-label',
      type: 'symbol',
      source: 'results',
      minzoom: 11,
      layout: {
        'text-field': ['get', 'label'],
        'text-size': 10,
        'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
        'text-offset': [0, -1.4],
      },
      paint: {
        'text-color': '#1f2937',
        'text-halo-color': '#ffffff',
        'text-halo-width': 1,
      },
    });

    // Click handler — show popup
    m.on('click', 'results-fill', (e: MapMouseEvent) => {
      const feature = e.features?.[0];
      if (feature) {
        setPopupContent(feature.properties);
        setPopupPosition([e.point.x, e.point.y]);
      }
    });
    m.on('mouseenter', 'results-fill', () => { m.getCanvas().style.cursor = 'pointer'; });
    m.on('mouseleave', 'results-fill', () => { m.getCanvas().style.cursor = ''; });
  }, [currentAnalysis, mapLoaded]);

  const startDraw = (mode: 'polygon' | 'rectangle') => {
    setDrawMode(mode);
    setSelectedCoords([]);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!drawMode || !map.current) return;

    const rect = mapContainer.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const lngLat = map.current.unproject([x, y]);
    const newCoord: [number, number] = [lngLat.lng, lngLat.lat];

    setSelectedCoords((prev) => [...prev, newCoord]);

    // Auto-close rectangle after 2 points
    if (drawMode === 'rectangle' && selectedCoords.length === 1) {
      completeAOI([...selectedCoords, newCoord]);
    }
  };

  const completeAOI = (coords: [number, number][]) => {
    if (coords.length < 3) return;

    // Close polygon
    if (coords[coords.length - 1] !== coords[0]) {
      coords.push(coords[0]);
    }

    const aoiPolygon: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [coords],
    };

    setAoi(aoiPolygon);
    setDrawMode(null);
    setSelectedCoords([]);
  };

  const handleRunAnalysis = async (analysisId?: string) => {
    if (!currentAoi) {
      alert(t('mapquery.selectarea'));
      return;
    }

    setIsProcessing(true);
    try {
      const analysis = await apiService.runAnalysis({
        aoi_geom: currentAoi,
        assessment_type: analysisId ? 'both' : assessmentType,
        personas_requested: personasRequested,
      });
      setAnalysis(analysis);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClearAoi = () => {
    setAoi(null);
    setDrawMode(null);
    setSelectedCoords([]);
    if (map.current) {
      if (map.current.getSource('aoi')) {
        map.current.removeLayer('aoi-fill');
        map.current.removeLayer('aoi-outline');
        map.current.removeSource('aoi');
      }
    }
  };

  const handleExport = () => {
    navigate('/reports');
  };

  return (
    <div
      className="relative w-full h-full overflow-hidden flex gap-4 p-4 bg-gray-50"
      onClick={drawMode ? handleCanvasClick : undefined}
    >
      {/* Left Panel: Layers */}
      {mapLayerPanelOpen && (
        <div className="w-64 bg-white rounded-lg shadow-md overflow-y-auto">
          <MapLayerPanel />
        </div>
      )}

      {/* Center: Map */}
      <div className="flex-1 bg-gray-200 rounded-lg overflow-hidden shadow-md relative min-h-0">
        <div ref={mapContainer} className="absolute inset-0" />

        {/* Popup */}
        {popupPosition && popupContent && (
          <ResultsPopup position={popupPosition} content={popupContent} />
        )}

        {/* AOI Inspector — shown when AOI drawn AND no analysis yet */}
        {aoiInspection && !currentAnalysis && (
          <div className="absolute top-4 right-4 z-20 pointer-events-auto">
            <AoiInspectorPanel
              inspection={aoiInspection}
              onRunAnalysis={handleRunAnalysis}
              onClearAoi={handleClearAoi}
              isProcessing={isProcessing}
            />
          </div>
        )}

        {/* Results Panel — shown after analysis completes */}
        {currentAnalysis?.results?.length && (() => {
          const CLASSES = [
            { cls: 'S1', label: 'Highly Suitable',        desc: 'No significant limitations for the intended use.',           color: '#166534', bg: '#dcfce7' },
            { cls: 'S2', label: 'Moderately Suitable',    desc: 'Minor limitations that may reduce productivity or benefit.',  color: '#16a34a', bg: '#bbf7d0' },
            { cls: 'S3', label: 'Marginally Suitable',    desc: 'Limitations that reduce productivity; special management needed.', color: '#ca8a04', bg: '#fef9c3' },
            { cls: 'S4', label: 'Currently Unsuitable',   desc: 'Limitations severe enough to prevent sustainable use under current conditions.', color: '#ea580c', bg: '#ffedd5' },
            { cls: 'S5', label: 'Permanently Unsuitable', desc: 'Limitations so severe that sustainable use is not possible.',  color: '#991b1b', bg: '#fee2e2' },
          ] as const;
          const total = currentAnalysis.results!.length;

          const ALL_ANALYSES = [
            { id: 'development-suitability',  icon: '🏗️', title: 'Development Suitability',    category: 'Suitability'    },
            { id: 'agriculture-suitability',  icon: '🌾', title: 'Agricultural Suitability',   category: 'Suitability'    },
            { id: 'cyclone-risk',             icon: '🌀', title: 'Cyclone Hazard Risk',         category: 'Hazard'         },
            { id: 'flood-risk',               icon: '🌊', title: 'Flood Risk Assessment',       category: 'Hazard'         },
            { id: 'tsunami-vulnerability',    icon: '🌊', title: 'Tsunami Vulnerability',       category: 'Hazard'         },
            { id: 'earthquake-hazard',        icon: '📳', title: 'Earthquake Hazard',           category: 'Hazard'         },
            { id: 'volcanic-hazard',          icon: '🌋', title: 'Volcanic Hazard',             category: 'Hazard'         },
            { id: 'landslide-risk',           icon: '🏔️', title: 'Landslide Risk',              category: 'Hazard'         },
            { id: 'infrastructure-assessment',icon: '🛣️', title: 'Infrastructure Assessment',   category: 'Infrastructure' },
            { id: 'building-vulnerability',   icon: '🏚️', title: 'Building Vulnerability',      category: 'Infrastructure' },
            { id: 'coastal-erosion',          icon: '🏝️', title: 'Coastal Erosion',             category: 'Environment'    },
            { id: 'biodiversity',             icon: '🦜', title: 'Biodiversity & Conservation', category: 'Environment'    },
          ];

          return (
            <div
              className="absolute top-4 right-4 z-20 pointer-events-auto flex flex-col bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
              style={{ width: 340, maxHeight: 'calc(100vh - 120px)' }}
            >
              {/* ── Header ── */}
              <div className="bg-gradient-to-r from-green-700 to-green-600 px-4 py-3 flex items-center justify-between shrink-0">
                <div>
                  <h3 className="text-white font-bold text-sm">✅ Analysis Complete</h3>
                  <p className="text-green-200 text-xs mt-0.5">
                    {total} grid points classified across drawn area
                  </p>
                </div>
                <button
                  onClick={() => setAnalysis(null as unknown as typeof currentAnalysis)}
                  className="text-green-300 hover:text-white text-xs border border-green-500 hover:border-white rounded px-2 py-0.5 transition-colors"
                >
                  ✕ Clear
                </button>
              </div>

              {/* Scrollable body */}
              <div className="overflow-y-auto flex-1 min-h-0">

                {/* ── Suitability breakdown bars ── */}
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Suitability Classification
                  </p>
                  <div className="space-y-1.5">
                    {CLASSES.map(({ cls, label, color, bg }) => {
                      const count = currentAnalysis.results!.filter(r => r.suitabilityClass === cls).length;
                      const pct   = Math.round((count / total) * 100);
                      if (count === 0) return null;
                      return (
                        <div key={cls} className="flex items-center gap-2">
                          <span
                            className="text-[10px] font-bold w-7 text-center rounded shrink-0 py-0.5"
                            style={{ color, background: bg }}
                          >
                            {cls}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-0.5">
                              <span className="text-xs font-medium text-gray-700 truncate">{label}</span>
                              <span className="text-xs text-gray-500 ml-2 shrink-0">{count} ({pct}%)</span>
                            </div>
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{ width: `${pct}%`, background: color }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* ── Suitability class legend with full descriptions ── */}
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Suitability Class Legend
                  </p>
                  <div className="space-y-2">
                    {CLASSES.map(({ cls, label, desc, color, bg }) => (
                      <div key={cls} className="flex items-start gap-2">
                        <span
                          className="text-[10px] font-bold w-7 text-center rounded shrink-0 mt-0.5 py-0.5"
                          style={{ color, background: bg }}
                        >
                          {cls}
                        </span>
                        <div>
                          <p className="text-xs font-semibold text-gray-800">{label}</p>
                          <p className="text-[10px] text-gray-500 leading-snug">{desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── All available analyses ── */}
                <div className="px-4 py-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    All Available Analyses
                  </p>
                  <div className="space-y-0.5">
                    {ALL_ANALYSES.map(a => (
                      <div
                        key={a.id}
                        className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-gray-50 group transition-colors border border-transparent hover:border-gray-200 cursor-pointer"
                        onClick={() => handleRunAnalysis(a.id)}
                      >
                        <span className="text-base shrink-0">{a.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-900 truncate">{a.title}</p>
                          <p className="text-[10px] text-gray-400">{a.category}</p>
                        </div>
                        <button
                          disabled={isProcessing}
                          className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 text-[10px] font-semibold bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
                        >
                          Run
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* ── Footer CTAs ── */}
              <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 flex flex-col gap-2 shrink-0">
                <button
                  onClick={() => navigate('/reports')}
                  className="w-full py-2 px-4 bg-green-600 text-white rounded-lg font-semibold text-sm hover:bg-green-700 active:scale-95 transition-all flex items-center justify-center gap-2"
                >
                  📄 Generate Report
                </button>
                <button
                  onClick={handleClearAoi}
                  className="w-full py-1.5 px-4 bg-white text-gray-600 border border-gray-300 rounded-lg text-xs font-medium hover:bg-gray-100 transition-all"
                >
                  Draw New Area
                </button>
              </div>
            </div>
          );
        })()}

        {/* Draw Mode Indicator */}
        {drawMode && (
          <div className="absolute top-4 left-4 bg-white px-4 py-2 rounded-lg shadow-md">
            <p className="text-sm font-medium text-gray-900">
              {drawMode === 'polygon' ? 'Drawing Polygon' : 'Drawing Rectangle'}
            </p>
            <p className="text-xs text-gray-600">
              Points: {selectedCoords.length} | Click to add point | Double-click to finish
            </p>
            <button
              onClick={() => {
                completeAOI(selectedCoords);
              }}
              className="mt-2 px-3 py-1 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
            >
              Finish Drawing
            </button>
          </div>
        )}

        {/* Draw Tools */}
        <div className="absolute bottom-4 left-4 flex gap-2">
          {(['polygon', 'rectangle'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => startDraw(mode)}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                drawMode === mode
                  ? 'bg-green-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100 shadow'
              }`}
            >
              {mode === 'polygon' ? '✏️ Polygon' : '⬛ Rectangle'}
            </button>
          ))}
          {selectedCoords.length > 0 && (
            <button
              onClick={() => { setDrawMode(null); setSelectedCoords([]); }}
              className="px-3 py-1 rounded text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 shadow"
            >
              ✕ Clear
            </button>
          )}
        </div>

        {/* Base Map Toggle — bottom-right (clear of Inspector Panel) */}
        <div className="absolute bottom-4 right-4 flex gap-2">
          {(['satellite', 'osm', 'topographic'] as const).map((base) => (
            <button
              key={base}
              onClick={() => setBaseMap(base)}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                baseMap === base
                  ? 'bg-green-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {base.charAt(0).toUpperCase() + base.slice(1)}
            </button>
          ))}
        </div>

        {/* OSM Layer Loading Status */}
        {Object.values(osmStatus).some(s => s === 'loading' || s === 'idle') && (
          <div className="absolute bottom-16 left-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg px-3 py-2 text-xs space-y-1 min-w-[180px]">
            <p className="font-semibold text-gray-700 mb-1">Loading GIS Layers</p>
            {([
              { key: 'buildings', label: '🏠 Buildings', color: '#d4956a' },
              { key: 'roads',     label: '🛣️ Roads',     color: '#888' },
              { key: 'waterways', label: '🌊 Rivers & Streams', color: '#4a90d9' },
              { key: 'parks',     label: '🌿 Parks',     color: '#55a630' },
            ] as const).map(({ key, label, color }) => {
              const s = osmStatus[key];
              return (
                <div key={key} className="flex items-center gap-2">
                  <span style={{ color }} className="w-3 text-center">
                    {s === 'loaded' ? '✓' : s === 'error' ? '✗' : s === 'loading' ? '⟳' : '○'}
                  </span>
                  <span className={s === 'loaded' ? 'text-gray-600' : s === 'error' ? 'text-red-500' : 'text-gray-400'}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* OSM Layers Loaded Badge */}
        {Object.values(osmStatus).every(s => s === 'loaded' || s === 'error') && (
          <div className="absolute bottom-16 left-4 bg-green-600/90 text-white rounded-lg shadow px-3 py-1.5 text-xs font-medium flex items-center gap-1.5">
            <span>✓</span> GIS layers loaded from OpenStreetMap
          </div>
        )}

        {/* Processing Overlay */}
        {isProcessing && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-lg">
            <div className="bg-white rounded-lg p-8 text-center">
              <div className="animate-spin w-12 h-12 border-4 border-green-200 border-t-green-600 rounded-full mx-auto mb-4" />
              <p className="text-gray-900 font-medium">{t('mapquery.processing')}</p>
            </div>
          </div>
        )}
      </div>

      {/* Right Panel: Query */}
      {queryPanelOpen && (
        <div className="w-72 bg-white rounded-lg shadow-md overflow-y-auto">
          <QueryPanel
            onRunAnalysis={handleRunAnalysis}
            onExport={handleExport}
            isProcessing={isProcessing}
            hasResults={!!currentAnalysis?.results}
          />
        </div>
      )}
    </div>
  );
}

// Helper functions — returns a MapLibre StyleSpecification object or URL string
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getMapStyle(baseMap: string): any {
  const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY || '';
  if (MAPTILER_KEY) {
    const styles: Record<string, string> = {
      satellite: `https://api.maptiler.com/maps/satellite/style.json?key=${MAPTILER_KEY}`,
      osm: `https://api.maptiler.com/maps/openstreetmap/style.json?key=${MAPTILER_KEY}`,
      topographic: `https://api.maptiler.com/maps/topo/style.json?key=${MAPTILER_KEY}`,
    };
    return styles[baseMap] || styles.osm;
  }

  // Free raster tile styles — CARTO CDN tiles have open CORS headers
  const cartoLight = [
    'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
    'https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
    'https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
  ];
  const cartoSatBase = [
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  ];
  const osmTiles = [
    'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
  ];

  const freeStyles: Record<string, object> = {
    osm: {
      version: 8,
      glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      sources: {
        carto: {
          type: 'raster',
          tiles: cartoLight,
          tileSize: 256,
          attribution: '© <a href="https://carto.com">CARTO</a> © <a href="https://openstreetmap.org">OSM</a>',
          maxzoom: 19,
        },
      },
      layers: [{ id: 'carto-base', type: 'raster', source: 'carto' }],
    },
    satellite: {
      version: 8,
      sources: {
        esri: {
          type: 'raster',
          tiles: cartoSatBase,
          tileSize: 256,
          attribution: 'Tiles © Esri — Source: Esri, Maxar, GeoEye',
          maxzoom: 19,
        },
      },
      layers: [{ id: 'esri-satellite', type: 'raster', source: 'esri' }],
    },
    topographic: {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: osmTiles,
          tileSize: 256,
          attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
          maxzoom: 19,
        },
      },
      layers: [{ id: 'osm-topo', type: 'raster', source: 'osm' }],
    },
  };

  return freeStyles[baseMap] || freeStyles.osm;
}

function addHazardLayers(map: MapLibreMap) {
  // Add demo hazard layers
  const hazards = ['cyclone', 'tsunami', 'volcanic', 'flood', 'earthquake', 'landslide'];

  hazards.forEach((hazard) => {
    // These would be actual data sources in production
    // For now, we add placeholder sources
    if (!map.getSource(hazard)) {
      map.addSource(hazard, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });
    }
  });
}

function addSuitabilityLayers(map: MapLibreMap) {
  // Add suitability layer source
  if (!map.getSource('suitability')) {
    map.addSource('suitability', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [],
      },
    });
  }
}
