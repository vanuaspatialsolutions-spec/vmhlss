import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import maplibregl, { Map as MapLibreMap, LngLatBounds, LngLatLike, MapMouseEvent } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useAuthStore, useAnalysisStore, useMapStore, useUIStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import MapLayerPanel from '../map/MapLayerPanel';
import QueryPanel from '../map/QueryPanel';
import ResultsPopup from '../map/ResultsPopup';
import type { GeoJSON } from '../../types/index';

export default function MapQueryWorkspace() {
  const navigate = useNavigate();
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
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

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: getMapStyle(baseMap),
      center: mapCenter,
      zoom: mapZoom,
      pitch: 0,
      bearing: 0,
    });

    map.current.on('move', () => {
      if (map.current) {
        setMapCenter([map.current.getCenter().lng, map.current.getCenter().lat]);
        setMapZoom(map.current.getZoom());
      }
    });

    // Add baseline layers
    map.current.on('load', () => {
      if (!map.current) return;

      // Add background layer
      map.current.addLayer({
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#f0f0f0' },
      });

      // Add demo hazard layers
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

  // Display results on map
  useEffect(() => {
    if (!map.current || !currentAnalysis?.results) return;

    // Remove existing results layer
    if (map.current.getSource('results')) {
      map.current.removeLayer('results-fill');
      map.current.removeSource('results');
    }

    // Create GeoJSON from results
    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: currentAnalysis.results.map((result) => ({
        type: 'Feature',
        geometry: result.geometry,
        properties: {
          suitabilityClass: result.suitabilityClass,
          chiScore: result.chiScore,
          confidence: result.confidence,
          topHazards: result.topHazards,
        },
      })),
    };

    map.current.addSource('results', {
      type: 'geojson',
      data: geojson,
    });

    map.current.addLayer({
      id: 'results-fill',
      type: 'circle',
      source: 'results',
      paint: {
        'circle-radius': 6,
        'circle-color': [
          'match',
          ['get', 'suitabilityClass'],
          'S1',
          '#1a5c30',
          'S2',
          '#4aa040',
          'S3',
          '#c8a000',
          'S4',
          '#c85000',
          'S5',
          '#8b2000',
          '#1a1a1a',
        ],
        'circle-opacity': 0.8,
      },
    });

    // Add click handler
    map.current.on('click', 'results-fill', (e: MapMouseEvent) => {
      const feature = e.features?.[0];
      if (feature) {
        setPopupContent(feature.properties);
        // Use screen pixel coordinates for popup placement
        setPopupPosition([e.point.x, e.point.y]);
      }
    });

    map.current.getCanvas().style.cursor = 'pointer';
  }, [currentAnalysis]);

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

  const handleRunAnalysis = async () => {
    if (!currentAoi) {
      alert(t('mapquery.selectarea'));
      return;
    }

    setIsProcessing(true);
    try {
      const analysis = await apiService.runAnalysis({
        aoi_geom: currentAoi,
        assessment_type: assessmentType,
        personas_requested: personasRequested,
      });
      setAnalysis(analysis);
    } catch (error) {
      console.error('Analysis failed:', error);
      alert('Analysis failed. Please try again.');
    } finally {
      setIsProcessing(false);
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
      <div className="flex-1 bg-gray-200 rounded-lg overflow-hidden shadow-md relative">
        <div ref={mapContainer} className="w-full h-full" />

        {/* Popup */}
        {popupPosition && popupContent && (
          <ResultsPopup position={popupPosition} content={popupContent} />
        )}

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

        {/* Base Map Toggle */}
        <div className="absolute top-4 right-4 flex gap-2">
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

// Helper functions — returns a MapLibre style object (or URL string with API key)
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
  // Fallback: inline raster styles using free tile providers (no API key needed)
  const freeStyles: Record<string, object> = {
    osm: {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxzoom: 19,
        },
      },
      layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
    },
    satellite: {
      version: 8,
      sources: {
        esri: {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          ],
          tileSize: 256,
          attribution: 'Tiles © Esri',
          maxzoom: 19,
        },
      },
      layers: [{ id: 'esri-satellite', type: 'raster', source: 'esri' }],
    },
    topographic: {
      version: 8,
      sources: {
        topo: {
          type: 'raster',
          tiles: ['https://tile.opentopomap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© <a href="https://opentopomap.org">OpenTopoMap</a>',
          maxzoom: 17,
        },
      },
      layers: [{ id: 'topo', type: 'raster', source: 'topo' }],
    },
  };
  // Return the object directly — MapLibre accepts StyleSpecification objects
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
