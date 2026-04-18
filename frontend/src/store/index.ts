import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  User,
  Language,
  GeoJSON,
  Analysis,
  AssessmentType,
  DatasetSlot,
  DatasetUpload,
  DashboardMetrics,
} from '../types/index';

// ============================================================================
// AUTH STORE
// ============================================================================
interface AuthStore {
  user: User | null;
  token: string | null;
  language: Language;
  setUser: (user: User) => void;
  setToken: (token: string) => void;
  setLanguage: (lang: Language) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      language: 'en',
      setUser: (user: User) => set({ user }),
      setToken: (token: string) => set({ token }),
      setLanguage: (lang: Language) => set({ language: lang }),
      logout: () => set({ user: null, token: null }),
      isAuthenticated: () => !!get().token && !!get().user,
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        language: state.language,
      }),
    }
  )
);

// ============================================================================
// ANALYSIS STORE
// ============================================================================
interface AnalysisStore {
  currentAoi: GeoJSON.Polygon | null;
  currentAnalysis: Analysis | null;
  assessmentType: AssessmentType;
  personasRequested: string[];
  analysisHistory: Analysis[];
  isProcessing: boolean;

  setAoi: (aoi: GeoJSON.Polygon | null) => void;
  setAnalysis: (analysis: Analysis) => void;
  setAssessmentType: (type: AssessmentType) => void;
  setPersonas: (personas: string[]) => void;
  setIsProcessing: (processing: boolean) => void;
  addToHistory: (analysis: Analysis) => void;
  clearCurrent: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  currentAoi: null,
  currentAnalysis: null,
  assessmentType: 'both',
  personasRequested: [],
  analysisHistory: [],
  isProcessing: false,

  setAoi: (aoi) => set({ currentAoi: aoi }),
  setAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  setAssessmentType: (type) => set({ assessmentType: type }),
  setPersonas: (personas) => set({ personasRequested: personas }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  addToHistory: (analysis) =>
    set((state) => ({
      analysisHistory: [analysis, ...state.analysisHistory].slice(0, 50),
    })),
  clearCurrent: () => set({ currentAoi: null, currentAnalysis: null }),
}));

// ============================================================================
// DATASET STORE
// ============================================================================
interface DatasetStore {
  slots: DatasetSlot[];
  uploads: Record<string, DatasetUpload>;
  qaReports: Record<string, any>;
  isLoading: boolean;
  error: string | null;

  setSlots: (slots: DatasetSlot[]) => void;
  updateSlot: (code: string, slot: Partial<DatasetSlot>) => void;
  addUpload: (upload: DatasetUpload) => void;
  removeUpload: (uploadId: string) => void;
  updateUpload: (uploadId: string, upload: Partial<DatasetUpload>) => void;
  setQAReport: (uploadId: string, report: any) => void;
  setIsLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clear: () => void;
}

export const useDatasetStore = create<DatasetStore>((set) => ({
  slots: [],
  uploads: {},
  qaReports: {},
  isLoading: false,
  error: null,

  setSlots: (slots) => set({ slots }),
  updateSlot: (code, slot) =>
    set((state) => ({
      slots: state.slots.map((s) => (s.code === code ? { ...s, ...slot } : s)),
    })),
  addUpload: (upload) =>
    set((state) => ({
      uploads: { ...state.uploads, [upload.id]: upload },
    })),
  removeUpload: (uploadId) =>
    set((state) => {
      const { [uploadId]: _, ...rest } = state.uploads;
      return { uploads: rest };
    }),
  updateUpload: (uploadId, upload) =>
    set((state) => ({
      uploads: {
        ...state.uploads,
        [uploadId]: { ...state.uploads[uploadId], ...upload },
      },
    })),
  setQAReport: (uploadId, report) =>
    set((state) => ({
      qaReports: { ...state.qaReports, [uploadId]: report },
    })),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  clear: () =>
    set({
      slots: [],
      uploads: {},
      qaReports: {},
      isLoading: false,
      error: null,
    }),
}));

// ============================================================================
// UI STORE
// ============================================================================
interface UIStore {
  activeWorkspace: string;
  mapLayers: Record<string, boolean>;
  sidebarOpen: boolean;
  mapLayerPanelOpen: boolean;
  queryPanelOpen: boolean;
  selectedResultCell: string | null;
  dashboardMetrics: DashboardMetrics | null;

  setActiveWorkspace: (workspace: string) => void;
  toggleLayer: (layerId: string) => void;
  setMapLayers: (layers: Record<string, boolean>) => void;
  setSidebarOpen: (open: boolean) => void;
  setMapLayerPanelOpen: (open: boolean) => void;
  setQueryPanelOpen: (open: boolean) => void;
  setSelectedResultCell: (cellId: string | null) => void;
  setDashboardMetrics: (metrics: DashboardMetrics) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  activeWorkspace: 'mapquery',
  mapLayers: {
    cyclone: false,
    tsunami: false,
    volcanic: false,
    flood: false,
    earthquake: false,
    landslide: false,
    chi: false,
    suitability: false,
    lulc: false,
    boundaries: true,
    knowledgeBase: false,
  },
  sidebarOpen: true,
  mapLayerPanelOpen: true,
  queryPanelOpen: true,
  selectedResultCell: null,
  dashboardMetrics: null,

  setActiveWorkspace: (workspace) => set({ activeWorkspace: workspace }),
  toggleLayer: (layerId) =>
    set((state) => ({
      mapLayers: {
        ...state.mapLayers,
        [layerId]: !state.mapLayers[layerId],
      },
    })),
  setMapLayers: (layers) => set({ mapLayers: layers }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setMapLayerPanelOpen: (open) => set({ mapLayerPanelOpen: open }),
  setQueryPanelOpen: (open) => set({ queryPanelOpen: open }),
  setSelectedResultCell: (cellId) => set({ selectedResultCell: cellId }),
  setDashboardMetrics: (metrics) => set({ dashboardMetrics: metrics }),
}));

// ============================================================================
// MAP STORE
// ============================================================================
interface MapStore {
  mapCenter: [number, number];
  mapZoom: number;
  baseMap: 'satellite' | 'osm' | 'topographic';
  aoiGeometry: GeoJSON.Polygon | null;

  setMapCenter: (center: [number, number]) => void;
  setMapZoom: (zoom: number) => void;
  setBaseMap: (base: 'satellite' | 'osm' | 'topographic') => void;
  setAoiGeometry: (geometry: GeoJSON.Polygon | null) => void;
}

export const useMapStore = create<MapStore>((set) => ({
  mapCenter: [166.959, -15.376], // [lng, lat] — Vanuatu (MapLibre expects lng first)
  mapZoom: 7,
  baseMap: 'osm',
  aoiGeometry: null,

  setMapCenter: (center) => set({ mapCenter: center }),
  setMapZoom: (zoom) => set({ mapZoom: zoom }),
  setBaseMap: (base) => set({ baseMap: base }),
  setAoiGeometry: (geometry) => set({ aoiGeometry: geometry }),
}));
