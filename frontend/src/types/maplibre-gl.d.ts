// Type declaration shim for maplibre-gl
// The dist/maplibre-gl.d.ts from the npm package was not installed in this environment.
// This provides the minimal types needed by the application.
// In production, the full maplibre-gl package ships with complete bundled types.
declare module 'maplibre-gl' {
  export type LngLatLike =
    | { lng: number; lat: number }
    | { lon: number; lat: number }
    | [number, number]
    | [number, number, number];

  export type LngLatBoundsLike =
    | LngLatBounds
    | [LngLatLike, LngLatLike]
    | [number, number, number, number]
    | LngLatLike;

  export class LngLatBounds {
    constructor(sw?: LngLatLike, ne?: LngLatLike);
    extend(obj: LngLatLike | LngLatBoundsLike): this;
    getCenter(): LngLat;
    getSouthWest(): LngLat;
    getNorthEast(): LngLat;
    toArray(): [[number, number], [number, number]];
    toString(): string;
    isEmpty(): boolean;
  }

  export class LngLat {
    lng: number;
    lat: number;
    constructor(lng: number, lat: number);
    toArray(): [number, number];
    toString(): string;
    distanceTo(lngLat: LngLat): number;
  }

  export type MapMouseEvent = {
    lngLat: LngLat;
    point: { x: number; y: number };
    features?: MapGeoJSONFeature[];
    originalEvent: MouseEvent;
  };

  export type MapGeoJSONFeature = {
    type: 'Feature';
    geometry: any;
    properties: Record<string, any>;
    layer: LayerSpecification;
    source: string;
    sourceLayer?: string;
  };

  export type StyleSpecification = any;
  export type LayerSpecification = any;
  export type SourceSpecification = any;

  export type FitBoundsOptions = {
    padding?: number | { top: number; bottom: number; left: number; right: number };
    maxZoom?: number;
    duration?: number;
    animate?: boolean;
    offset?: [number, number];
  };

  export type Point = {
    x: number;
    y: number;
  };

  export class Map {
    constructor(options: {
      container: string | HTMLElement;
      style?: string | StyleSpecification;
      center?: LngLatLike;
      zoom?: number;
      pitch?: number;
      bearing?: number;
      minZoom?: number;
      maxZoom?: number;
      attributionControl?: boolean;
    });
    addControl(control: any, position?: string): this;
    removeControl(control: any): this;
    on(type: string, layerOrHandler: string | ((e: any) => void), handler?: (e: any) => void): this;
    off(type: string, layerOrHandler: string | ((e: any) => void), handler?: (e: any) => void): this;
    once(type: string, handler: (e: any) => void): this;
    addSource(id: string, source: SourceSpecification | any): this;
    removeSource(id: string): this;
    getSource(id: string): any;
    addLayer(layer: LayerSpecification | any, before?: string): this;
    removeLayer(id: string): this;
    getLayer(id: string): LayerSpecification | undefined;
    setFilter(layerId: string, filter: any): this;
    setPaintProperty(layerId: string, name: string, value: any): this;
    setLayoutProperty(layerId: string, name: string, value: any): this;
    setStyle(style: string | StyleSpecification): this;
    getStyle(): StyleSpecification;
    fitBounds(bounds: LngLatBoundsLike, options?: FitBoundsOptions): this;
    flyTo(options: any): this;
    setCenter(center: LngLatLike): this;
    getCenter(): LngLat;
    setZoom(zoom: number): this;
    getZoom(): number;
    unproject(point: Point | [number, number]): LngLat;
    project(lngLat: LngLatLike): Point;
    getCanvas(): HTMLCanvasElement;
    getContainer(): HTMLElement;
    remove(): void;
    resize(): this;
    loaded(): boolean;
    queryRenderedFeatures(pointOrBox?: any, options?: any): MapGeoJSONFeature[];
    setTerrain(options: any | null): this;
    isStyleLoaded(): boolean;
  }

  export class Marker {
    constructor(options?: { element?: HTMLElement; color?: string; scale?: number });
    setLngLat(lngLat: LngLatLike): this;
    getLngLat(): LngLat;
    addTo(map: Map): this;
    remove(): this;
    getElement(): HTMLElement;
  }

  export class Popup {
    constructor(options?: { closeButton?: boolean; closeOnClick?: boolean; offset?: number });
    setLngLat(lngLat: LngLatLike): this;
    setHTML(html: string): this;
    setText(text: string): this;
    addTo(map: Map): this;
    remove(): this;
    isOpen(): boolean;
  }

  export class NavigationControl {
    constructor(options?: { showCompass?: boolean; showZoom?: boolean; visualizePitch?: boolean });
  }

  export class AttributionControl {
    constructor(options?: { compact?: boolean; customAttribution?: string | string[] });
  }

  export class ScaleControl {
    constructor(options?: { maxWidth?: number; unit?: 'imperial' | 'metric' | 'nautical' });
  }

  export class FullscreenControl {
    constructor(options?: { container?: HTMLElement });
  }

  const maplibregl: {
    Map: typeof Map;
    Marker: typeof Marker;
    Popup: typeof Popup;
    LngLat: typeof LngLat;
    LngLatBounds: typeof LngLatBounds;
    NavigationControl: typeof NavigationControl;
    AttributionControl: typeof AttributionControl;
    ScaleControl: typeof ScaleControl;
    FullscreenControl: typeof FullscreenControl;
    accessToken: string;
    version: string;
  };

  export default maplibregl;
}
