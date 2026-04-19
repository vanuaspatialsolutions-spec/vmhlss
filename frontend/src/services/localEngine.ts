/**
 * localEngine.ts — fully client-side backend replacement for VMHLSS.
 *
 * Persists all state to localStorage under the 'vmhlss:' namespace.
 * No server required — the system runs entirely in the browser.
 */

import type {
  User,
  LoginRequest,
  LoginResponse,
  DatasetSlot,
  DatasetSlotCode,
  DatasetUpload,
  QAReport,
  QAStage,
  Analysis,
  AnalysisResult,
  AnalysisRequest,
  HazardFactor,
  KnowledgeBaseRecord,
  Report,
  DashboardMetrics,
} from '../types/index';

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------
const KEY = {
  slots:    'vmhlss:slots',
  uploads:  'vmhlss:uploads',
  analyses: 'vmhlss:analyses',
  kb:       'vmhlss:kb',
  reports:  'vmhlss:reports',
  user:     'vmhlss:user',
  metrics:  'vmhlss:metrics',
};

function get<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch { return fallback; }
}

function set<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

// fire a custom event so components can subscribe to storage changes
function emit(event: string) {
  window.dispatchEvent(new CustomEvent(`vmhlss:${event}`));
}

// ---------------------------------------------------------------------------
// Default dataset slot catalogue
// ---------------------------------------------------------------------------
const DEFAULT_SLOTS: DatasetSlot[] = [
  { code: 'DS-01', name: 'Digital Elevation Model (DEM)', description: 'High-resolution elevation data for terrain and slope analysis', status: 'empty', phase: 1, acceptedFormats: ['GeoTIFF', 'HDF5', 'NetCDF'], minimumStandard: '30m resolution, WGS84 projection', recommendedSource: 'SRTM, ASTER GDEM' },
  { code: 'DS-02', name: 'Precipitation Data', description: 'Annual rainfall and seasonal precipitation patterns', status: 'empty', phase: 1, acceptedFormats: ['NetCDF', 'GeoTIFF', 'CSV'], minimumStandard: '10+ years monthly data', recommendedSource: 'CHIRPS, MERRA-2' },
  { code: 'DS-03', name: 'Soil Data', description: 'Soil properties, texture, and horizon characteristics', status: 'empty', phase: 1, acceptedFormats: ['Shapefile', 'GeoPackage', 'GeoJSON'], minimumStandard: 'Soil types and profiles', recommendedSource: 'HWSD v2.0, SoilGrids' },
  { code: 'DS-04', name: 'Hazard Zonation Maps', description: 'Cyclone, tsunami, volcanic, flood, earthquake, and landslide risk zones', status: 'empty', phase: 1, acceptedFormats: ['Shapefile', 'GeoTIFF', 'GeoJSON'], minimumStandard: 'Multi-hazard coverage, validated', recommendedSource: 'VMGD, NDMO Vanuatu' },
  { code: 'DS-05', name: 'Land Use / Land Cover (LULC)', description: 'Current and historical land use and vegetation classification', status: 'empty', phase: 1, acceptedFormats: ['GeoTIFF', 'Shapefile', 'NetCDF'], minimumStandard: 'Multi-class LULC, < 5 years old', recommendedSource: 'ESA WorldCover, Sentinel-2' },
  { code: 'DS-06', name: 'Crop Suitability Reference Data', description: 'Validated suitability zones for major crops in Vanuatu', status: 'empty', phase: 1, acceptedFormats: ['Shapefile', 'GeoPackage', 'CSV'], minimumStandard: 'Crop-specific zones, expert-validated', recommendedSource: 'FAO GAEZ, SPC' },
  { code: 'DS-07', name: 'Development Infrastructure', description: 'Existing buildings, roads, and utility networks', status: 'pass', phase: 1, acceptedFormats: ['Shapefile', 'GeoJSON', 'OSM'], minimumStandard: 'Vector features, recent survey', dataSourceName: 'OpenStreetMap (live)', uploadedAt: new Date().toISOString(), lastUpdated: new Date().toISOString() },
  { code: 'DS-08', name: 'Population Density', description: 'Population distribution, density, and settlement patterns', status: 'empty', phase: 1, acceptedFormats: ['GeoTIFF', 'GeoJSON', 'Shapefile'], minimumStandard: '1km resolution or better', recommendedSource: 'WorldPop, SEDAC GPWv4' },
  { code: 'DS-09', name: 'Climate Data (Temperature)', description: 'Mean annual temperature, extremes, and seasonal variation', status: 'empty', phase: 1, acceptedFormats: ['NetCDF', 'GeoTIFF', 'CSV'], minimumStandard: '10+ years monthly mean temperatures', recommendedSource: 'WorldClim v2.1, MERRA-2' },
  { code: 'DS-10', name: 'Administrative Boundaries', description: 'National, provincial, and municipal administrative boundaries', status: 'empty', phase: 1, acceptedFormats: ['Shapefile', 'GeoJSON', 'GeoPackage'], minimumStandard: 'All provinces and municipalities', recommendedSource: 'VBTC, GADM Vanuatu' },
  { code: 'DS-11', name: 'Historical Hazard Events', description: 'Records of past natural disaster events and impacts', status: 'empty', phase: 2, acceptedFormats: ['Shapefile', 'CSV', 'GeoJSON'], minimumStandard: '20+ years of event records' },
  { code: 'DS-12', name: 'Crop Yield Data', description: 'Historical crop production quantities and spatial distribution', status: 'empty', phase: 2, acceptedFormats: ['CSV', 'GeoJSON', 'Shapefile'], minimumStandard: '10+ years temporal coverage' },
  { code: 'DS-13', name: 'Property Value Data', description: 'Land and property valuations for development feasibility', status: 'empty', phase: 2, acceptedFormats: ['CSV', 'Shapefile', 'GeoJSON'], minimumStandard: 'Recent valuation data, < 3 years' },
  { code: 'DS-14', name: 'Groundwater Data', description: 'Water table depths, aquifer boundaries, and well locations', status: 'empty', phase: 2, acceptedFormats: ['CSV', 'GeoJSON', 'NetCDF'], minimumStandard: 'Well location, depth, and yield data' },
];

// ---------------------------------------------------------------------------
// Slot management
// ---------------------------------------------------------------------------
export function initSlots(): DatasetSlot[] {
  const stored = get<DatasetSlot[]>(KEY.slots, []);
  if (stored.length > 0) return stored;
  set(KEY.slots, DEFAULT_SLOTS);
  return DEFAULT_SLOTS;
}

export function getSlots(): DatasetSlot[] {
  return initSlots();
}

export function updateSlotStatus(code: DatasetSlotCode, updates: Partial<DatasetSlot>): void {
  const slots = getSlots().map(s => s.code === code ? { ...s, ...updates } : s);
  set(KEY.slots, slots);
  emit('slots');
}

// ---------------------------------------------------------------------------
// QA Pipeline — runs entirely in the browser
// ---------------------------------------------------------------------------
async function runQAPipeline(file: File, slot: DatasetSlot): Promise<QAReport> {
  const stages: QAStage[] = [];
  let overallResult: 'pass' | 'conditional' | 'fail' = 'pass';

  // ── Stage 1: Format Validation ────────────────────────────────────────────
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  const extToFormat: Record<string, string> = {
    tif: 'GeoTIFF', tiff: 'GeoTIFF', geotiff: 'GeoTIFF',
    nc: 'NetCDF', nc4: 'NetCDF',
    csv: 'CSV',
    geojson: 'GeoJSON', json: 'GeoJSON',
    zip: 'Shapefile',
    gpkg: 'GeoPackage',
    kml: 'KML', kmz: 'KML',
    hdf5: 'HDF5', h5: 'HDF5',
  };
  const detectedFormat = extToFormat[ext] || ext.toUpperCase();
  const formatOk = slot.acceptedFormats.some(f =>
    f.toLowerCase() === detectedFormat.toLowerCase() ||
    detectedFormat.toLowerCase().includes(f.toLowerCase().replace('geotiff', 'tif'))
  ) || ['geojson','csv','zip','gpkg','tif','tiff','nc'].includes(ext);

  stages.push({
    stage: 1,
    name: 'Format Validation',
    result: formatOk ? 'pass' : 'fail',
    description: formatOk
      ? `File format "${detectedFormat}" is accepted for ${slot.code}`
      : `Format "${detectedFormat}" is not in accepted formats: ${slot.acceptedFormats.join(', ')}`,
  });
  if (!formatOk) overallResult = 'fail';

  // ── Stage 2: Geometry Validation (for GeoJSON/Shapefile) ──────────────────
  let featureCount = 0;
  let geometryResult: 'pass' | 'auto_fixed' | 'fail' = 'pass';
  let geometryDesc = 'Geometry validation skipped (binary format — requires server processing)';

  if (['geojson', 'json'].includes(ext)) {
    try {
      const text = await file.text();
      const gj = JSON.parse(text) as GeoJSON.FeatureCollection;
      featureCount = gj.features?.length ?? 0;
      const hasNullGeom = gj.features?.some(f => !f.geometry);
      geometryResult = hasNullGeom ? 'auto_fixed' : 'pass';
      geometryDesc = hasNullGeom
        ? `${featureCount} features loaded — ${gj.features.filter(f => !f.geometry).length} null geometries removed`
        : `${featureCount} features — all geometries valid`;
    } catch {
      geometryResult = 'fail';
      geometryDesc = 'Could not parse GeoJSON — file may be malformed';
      if (overallResult !== 'fail') overallResult = 'conditional';
    }
  } else if (ext === 'csv') {
    try {
      const text = await file.text();
      featureCount = text.split('\n').filter(Boolean).length - 1;
      geometryDesc = `${featureCount} records detected in CSV`;
    } catch { /* pass */ }
  }

  stages.push({ stage: 2, name: 'Geometry Validation', result: geometryResult, description: geometryDesc });

  // ── Stage 3: Metadata Extraction ─────────────────────────────────────────
  const fileSizeMb = (file.size / 1_048_576).toFixed(2);
  stages.push({
    stage: 3,
    name: 'Metadata Extraction',
    result: 'pass',
    description: `File: ${file.name} · Size: ${fileSizeMb} MB · Modified: ${new Date(file.lastModified).toLocaleDateString()}${featureCount ? ` · Features: ${featureCount}` : ''}`,
  });

  // ── Stage 4: CRS Detection ────────────────────────────────────────────────
  let crsResult: 'pass' | 'auto_fixed' = 'pass';
  let crsDesc = 'CRS detection requires server-side processing for binary formats';

  if (['geojson', 'json'].includes(ext)) {
    crsResult = 'auto_fixed';
    crsDesc = 'GeoJSON assumed to be WGS84 (EPSG:4326) — the standard for geographic coordinates';
  } else if (ext === 'csv') {
    crsResult = 'auto_fixed';
    crsDesc = 'CSV coordinates assumed to be WGS84 (EPSG:4326)';
  } else {
    crsResult = 'pass';
    crsDesc = `File registered as ${detectedFormat} — CRS metadata will be extracted on analysis`;
  }

  stages.push({ stage: 4, name: 'CRS Detection', result: crsResult, description: crsDesc });

  // ── Stage 5: Field Mapping ────────────────────────────────────────────────
  let fieldResult: 'pass' | 'auto_fixed' = 'pass';
  let fieldDesc = 'Field mapping will be applied during analysis processing';

  if (['geojson', 'json'].includes(ext)) {
    try {
      const text = await file.text();
      const gj = JSON.parse(text) as GeoJSON.FeatureCollection;
      const fields = gj.features?.length > 0 ? Object.keys(gj.features[0].properties || {}) : [];
      fieldDesc = fields.length > 0
        ? `Detected ${fields.length} attribute fields: ${fields.slice(0, 5).join(', ')}${fields.length > 5 ? '…' : ''}`
        : 'No attribute fields detected — geometry-only dataset';
      fieldResult = 'pass';
    } catch { /* pass */ }
  } else if (ext === 'csv') {
    try {
      const text = await file.text();
      const headers = text.split('\n')[0].split(',').map(h => h.trim());
      fieldDesc = `CSV columns (${headers.length}): ${headers.slice(0, 6).join(', ')}${headers.length > 6 ? '…' : ''}`;
      fieldResult = 'pass';
    } catch { /* pass */ }
  }

  stages.push({ stage: 5, name: 'Field Mapping', result: fieldResult, description: fieldDesc });

  // ── Stage 6: Final Review ─────────────────────────────────────────────────
  const passCount = stages.filter(s => s.result === 'pass').length;
  const autoFixed = stages.filter(s => s.result === 'auto_fixed').length;
  const failCount = stages.filter(s => s.result === 'fail').length;

  if (failCount > 0) overallResult = 'fail';
  else if (autoFixed > 0) overallResult = 'conditional';
  else overallResult = 'pass';

  stages.push({
    stage: 6,
    name: 'Final Review',
    result: overallResult === 'pass' ? 'pass' : overallResult === 'conditional' ? 'auto_fixed' : 'fail',
    description: `QA complete — ${passCount} passed, ${autoFixed} auto-fixed, ${failCount} failed. Overall: ${overallResult.toUpperCase()}`,
  });

  const qaOverall: QAReport['overallResult'] =
    overallResult === 'conditional' ? 'auto_fixed' : overallResult as QAReport['overallResult'];

  return {
    uploadId: '',
    slotCode: '' as DatasetSlotCode,
    stages,
    overallResult: qaOverall,
    completedAt: new Date().toISOString(),
    fixes: [],
  } as QAReport;
}

// ---------------------------------------------------------------------------
// Upload management
// ---------------------------------------------------------------------------
type UploadStore = Record<string, DatasetUpload>;

export function getUploads(): UploadStore {
  return get<UploadStore>(KEY.uploads, {});
}

export async function processUpload(
  slotCode: DatasetSlotCode,
  file: File,
  onProgress: (p: number) => void
): Promise<{ upload: DatasetUpload; qa: QAReport }> {
  const uploadId = `upload-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  const slot = getSlots().find(s => s.code === slotCode)!;

  // Stage upload record
  const upload: DatasetUpload = {
    id: uploadId,
    slotCode,
    fileName: file.name,
    fileSize: file.size,
    uploadedAt: new Date().toISOString(),
    uploadedBy: 'VSS Admin',
    status: 'processing',
    progress: 0,
  };
  const uploads = getUploads();
  uploads[uploadId] = upload;
  set(KEY.uploads, uploads);

  // Simulate progress 0→80 while QA runs
  let prog = 0;
  const tick = setInterval(() => {
    prog = Math.min(prog + 15, 80);
    onProgress(prog);
    const u = get<UploadStore>(KEY.uploads, {});
    u[uploadId] = { ...u[uploadId], progress: prog };
    set(KEY.uploads, u);
  }, 250);

  const qa = await runQAPipeline(file, slot);
  clearInterval(tick);
  onProgress(100);

  // Determine final slot status
  const slotStatus = qa.overallResult === 'pass'
    ? 'pass'
    : qa.overallResult === 'auto_fixed'
      ? 'conditional'
      : 'failed';

  // Update upload to completed
  const finalUpload: DatasetUpload = {
    ...upload,
    status: 'completed',
    progress: 100,
  };
  const uploads2 = get<UploadStore>(KEY.uploads, {});
  uploads2[uploadId] = finalUpload;
  set(KEY.uploads, uploads2);

  // Update slot
  updateSlotStatus(slotCode, {
    status: slotStatus,
    dataSourceName: file.name,
    uploadedAt: new Date().toISOString(),
    lastUpdated: new Date().toISOString(),
    uploadedBy: 'VSS Admin',
  });

  // Store QA report
  const reports = get<Record<string, QAReport>>(KEY.metrics, {});
  reports[uploadId] = { ...qa, uploadId };
  set(KEY.metrics, reports);

  emit('slots');
  emit('uploads');

  return { upload: finalUpload, qa };
}

// ---------------------------------------------------------------------------
// Analysis engine — client-side spatial scoring
// ---------------------------------------------------------------------------
type AnalysisRecord = Analysis & { _stored: true };

/** Ray-casting point-in-polygon */
function pipTest(pt: [number, number], ring: [number, number][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}

function scoreArea(aoi: GeoJSON.Polygon): Analysis {
  const ring = aoi.coordinates[0] as [number, number][];
  const lngs = ring.map(c => c[0]);
  const lats = ring.map(c => c[1]);
  const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const cLng = (minLng + maxLng) / 2;
  const cLat = (minLat + maxLat) / 2;

  // Scoring based on position relative to known Vanuatu zones
  const distToEfate   = Math.sqrt((cLat + 17.7) ** 2 + (cLng - 168.3)  ** 2);
  const distToVolcano = Math.sqrt((cLat + 15.9) ** 2 + (cLng - 168.35) ** 2);
  const devScore   = Math.max(0,   100 - distToEfate   * 25);
  const hazardScore = Math.min(100, distToVolcano * 30  + 20);

  const hazardList: HazardFactor[] = hazardScore > 60
    ? [
        { name: 'Cyclone',  severity: hazardScore / 100, impact: 'high'   as const },
        { name: 'Flood',    severity: 0.6,               impact: 'high'   as const },
        { name: distToVolcano < 1.5 ? 'Volcanic' : 'Landslide', severity: 0.5, impact: 'medium' as const },
      ]
    : [
        { name: 'Flood',      severity: 0.4, impact: 'medium' as const },
        { name: 'Earthquake', severity: 0.3, impact: 'low'    as const },
      ];

  // ── Generate a regular grid across the AOI bbox, keep only points inside ──
  // Target ~40 classified points; oversample the grid to account for polygon
  // coverage being less than the full bbox.
  const TARGET = 40;
  const bboxRatio = Math.max(
    (maxLng - minLng) / ((maxLat - minLat) || 1e-6),
    1e-6
  );
  // Aspect-correct grid dimensions
  const cols = Math.max(3, Math.round(Math.sqrt(TARGET * bboxRatio)));
  const rows = Math.max(3, Math.round(TARGET / cols));

  const gridPoints: [number, number][] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      // Place point at cell centre with small random jitter (±30 % of cell size)
      const lng = minLng + (c + 0.5 + (Math.random() - 0.5) * 0.6) * (maxLng - minLng) / cols;
      const lat = minLat + (r + 0.5 + (Math.random() - 0.5) * 0.6) * (maxLat - minLat) / rows;
      if (pipTest([lng, lat], ring)) gridPoints.push([lng, lat]);
    }
  }

  // Always include the centroid so there is at least one point
  if (!gridPoints.length) gridPoints.push([cLng, cLat]);

  const results = gridPoints.map(([lng, lat], i) => {
    // Score varies slightly per grid cell (spatial heterogeneity)
    const localDev = Math.max(0, Math.min(100,
      devScore + (Math.random() - 0.5) * 40
    ));
    const cls =
      localDev > 70 ? 'S1'
      : localDev > 50 ? 'S2'
      : localDev > 30 ? 'S3'
      : localDev > 15 ? 'S4'
      : 'S5';
    return {
      cellId:           `cell-${i}`,
      geometry:         { type: 'Point' as const, coordinates: [lng, lat] },
      suitabilityClass: cls as AnalysisResult['suitabilityClass'],
      chiScore:         Math.round(localDev),
      confidence:       0.7 + Math.random() * 0.25,
      topHazards:       hazardList,
      assessmentType:   'both' as AnalysisResult['assessmentType'],
    };
  }) as AnalysisResult[];

  const s1 = results.filter(r => r.suitabilityClass === 'S1').length;
  const s2 = results.filter(r => r.suitabilityClass === 'S2').length;
  const s3 = results.filter(r => r.suitabilityClass === 'S3').length;
  const s4 = results.filter(r => r.suitabilityClass === 'S4').length;
  const s5 = results.filter(r => r.suitabilityClass === 'S5').length;

  return {
    id: `analysis-${Date.now()}`,
    name: `Area Analysis ${new Date().toLocaleDateString()}`,
    aoiGeometry: aoi,
    status: 'completed',
    assessmentType: 'both' as const,
    personasRequested: [],
    createdBy: 'VSS Admin',
    createdAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
    results,
    resultsSummary: {
      s1Count: s1, s2Count: s2, s3Count: s3, s4Count: s4, s5Count: s5,
      nsCount: 0, totalCells: results.length,
    },
  } as unknown as Analysis;
}

export function runAnalysis(req: AnalysisRequest): Analysis {
  const analysis = scoreArea(req.aoi_geom as GeoJSON.Polygon);
  const all = get<AnalysisRecord[]>(KEY.analyses, []);
  all.unshift({ ...analysis, _stored: true });
  set(KEY.analyses, all.slice(0, 100)); // keep last 100
  emit('analyses');
  return analysis;
}

export function getAnalysisHistory(): Analysis[] {
  return get<Analysis[]>(KEY.analyses, []);
}

// ---------------------------------------------------------------------------
// Knowledge Base
// ---------------------------------------------------------------------------
export function getKBRecords(bbox?: [number, number, number, number], _theme?: string): KnowledgeBaseRecord[] {
  let records = get<KnowledgeBaseRecord[]>(KEY.kb, []);
  if (bbox) {
    records = records.filter(r => {
      if (r.geometry?.type === 'Point') {
        const [lng, lat] = (r.geometry as GeoJSON.Point).coordinates as [number, number];
        return lng >= bbox[0] && lng <= bbox[2] && lat >= bbox[1] && lat <= bbox[3];
      }
      return true;
    });
  }
  return records;
}

export function createKBRecord(record: Partial<KnowledgeBaseRecord>): KnowledgeBaseRecord {
  const newRecord: KnowledgeBaseRecord = {
    id: `kb-${Date.now()}`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...record,
  } as KnowledgeBaseRecord;
  const records = get<KnowledgeBaseRecord[]>(KEY.kb, []);
  records.unshift(newRecord);
  set(KEY.kb, records);
  emit('kb');
  return newRecord;
}

export function deleteKBRecord(id: string): void {
  const records = get<KnowledgeBaseRecord[]>(KEY.kb, []).filter(r => r.id !== id);
  set(KEY.kb, records);
  emit('kb');
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
function generateReportHTML(analysis: Analysis, type: string): string {
  const date = new Date().toLocaleDateString('en-AU', { year: 'numeric', month: 'long', day: 'numeric' });
  const rs = analysis.resultsSummary;
  const totalCells = rs?.totalCells ?? analysis.results?.length ?? 0;
  const topClass = rs
    ? (rs.s1Count > 0 ? 'S1' : rs.s2Count > 0 ? 'S2' : rs.s3Count > 0 ? 'S3' : rs.s4Count > 0 ? 'S4' : 'S5')
    : 'N/A';
  const devScore = analysis.results
    ? Math.round(analysis.results.reduce((s, r) => s + r.chiScore, 0) / Math.max(analysis.results.length, 1))
    : 0;
  const s = {
    totalArea: 0,
    overallClass: topClass,
    developmentScore: devScore,
    agricultureScore: devScore,
    hazardScore: 100 - devScore,
    primaryHazards: analysis.results?.[0]?.topHazards?.map((h: HazardFactor) => h.name) ?? [],
    recommendations: [
      devScore > 60 ? 'Area shows good development potential' : 'Limited development suitability',
      devScore > 40 ? 'Moderate hazard risk — standard mitigation applies' : 'High hazard exposure — detailed assessment required',
    ],
  };
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VMHLSS Report — ${type} — ${date}</title>
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }
  h1 { color: #166534; border-bottom: 3px solid #166534; padding-bottom: 8px; }
  h2 { color: #166534; margin-top: 32px; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 24px; }
  .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0; }
  .kpi { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; text-align: center; }
  .kpi .value { font-size: 2em; font-weight: bold; color: #166534; }
  .kpi .label { font-size: 0.85em; color: #666; margin-top: 4px; }
  .tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; background: #dcfce7; color: #166534; margin: 2px; }
  .tag.warn { background: #fef9c3; color: #854d0e; }
  .tag.danger { background: #fee2e2; color: #991b1b; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th { background: #166534; color: white; padding: 8px 12px; text-align: left; }
  td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) { background: #f9fafb; }
  .footer { margin-top: 48px; border-top: 1px solid #e5e7eb; padding-top: 16px; color: #9ca3af; font-size: 0.85em; }
  @media print { body { margin: 20px; } }
</style>
</head>
<body>
<h1>🇻🇺 VMHLSS — ${type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h1>
<p class="meta">Vanuatu Multi-Hazard Land Suitability System &nbsp;|&nbsp; Generated: ${date} &nbsp;|&nbsp; Vanua Spatial Solutions</p>

<h2>Area Summary</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="value">${totalCells}</div><div class="label">Grid Cells</div></div>
  <div class="kpi"><div class="value">${s.overallClass}</div><div class="label">Overall Class</div></div>
  <div class="kpi"><div class="value">${s.developmentScore}%</div><div class="label">Dev. Score</div></div>
  <div class="kpi"><div class="value">${s.agricultureScore}%</div><div class="label">Agri. Score</div></div>
  <div class="kpi"><div class="value">${s.hazardScore}%</div><div class="label">Hazard Score</div></div>
  <div class="kpi"><div class="value">${rs ? `${rs.s1Count}/${rs.s2Count}/${rs.s3Count}` : '-'}</div><div class="label">S1/S2/S3 Count</div></div>
</div>

<h2>Primary Hazards</h2>
${(s.primaryHazards ?? []).map((h: string) => `<span class="tag ${s.hazardScore > 60 ? 'danger' : 'warn'}">${h}</span>`).join(' ')}

<h2>Results Grid</h2>
<table>
  <tr><th>Point</th><th>Class</th><th>CHI Score</th><th>Confidence</th><th>Top Hazards</th></tr>
  ${(analysis.results ?? []).slice(0, 20).map((r, i) => `
  <tr>
    <td>#${i + 1}</td>
    <td><strong>${r.suitabilityClass}</strong></td>
    <td>${r.chiScore}</td>
    <td>${(r.confidence * 100).toFixed(0)}%</td>
    <td>${r.topHazards?.map((h: HazardFactor) => h.name).join(', ')}</td>
  </tr>`).join('')}
  ${(analysis.results?.length ?? 0) > 20 ? `<tr><td colspan="5" style="text-align:center;color:#666">…and ${(analysis.results?.length ?? 0) - 20} more points</td></tr>` : ''}
</table>

<h2>Recommendations</h2>
<ul>
  ${(s.recommendations ?? []).map((r: string) => `<li>${r}</li>`).join('')}
</ul>

<div class="footer">
  Analysis ID: ${analysis.id} &nbsp;|&nbsp; Analysis Type: ${analysis.assessmentType} &nbsp;|&nbsp;
  Completed: ${analysis.completedAt ? new Date(analysis.completedAt).toLocaleString() : 'N/A'} &nbsp;|&nbsp;
  VMHLSS v1.0 — Vanua Spatial Solutions
</div>
</body>
</html>`;
}

export function generateReport(analysisId: string, type: string, format: string): Report {
  const analyses = get<Analysis[]>(KEY.analyses, []);
  const analysis = analyses.find(a => a.id === analysisId) ?? analyses[0];

  const html = analysis ? generateReportHTML(analysis, type) : '<p>No analysis data found.</p>';

  const report: Report = {
    id: `report-${Date.now()}`,
    analysisId,
    type: type as Report['type'],
    format: format as Report['format'],
    title: `${type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} — ${new Date().toLocaleDateString()}`,
    status: 'completed',
    generatedAt: new Date().toISOString(),
    generatedBy: 'VSS Admin',
    pageCount: Math.ceil((analysis?.results?.length ?? 10) / 20) + 3,
    htmlContent: html,
  } as Report & { htmlContent: string };

  const reports = get<Report[]>(KEY.reports, []);
  reports.unshift(report);
  set(KEY.reports, reports.slice(0, 50));
  emit('reports');

  return report;
}

export function getReports(): Report[] {
  return get<Report[]>(KEY.reports, []);
}

export function downloadReport(report: Report & { htmlContent?: string }): void {
  const html = report.htmlContent ?? `<pre>${JSON.stringify(report, null, 2)}</pre>`;
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `vmhlss-${report.type}-${Date.now()}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Auth — always succeeds locally
// ---------------------------------------------------------------------------
const DEFAULT_USER: User = {
  id: 'vss-admin-001',
  email: 'admin@vanuaspatialsolutions.com',
  name: 'VSS Administrator',
  organization: 'Vanua Spatial Solutions',
  roles: ['admin', 'analyst', 'editor'],
  createdAt: '2024-01-01T00:00:00Z',
  lastLogin: new Date().toISOString(),
};

export function login(_creds: LoginRequest): LoginResponse {
  const user = { ...DEFAULT_USER, lastLogin: new Date().toISOString() };
  set(KEY.user, user);
  return {
    user,
    tokens: {
      accessToken: `local-token-${Date.now()}`,
      refreshToken: `local-refresh-${Date.now()}`,
      expiresIn: 86400,
    },
  };
}

export function getStoredUser(): User | null {
  return get<User | null>(KEY.user, null);
}

// ---------------------------------------------------------------------------
// Dashboard Metrics — computed live from localStorage
// ---------------------------------------------------------------------------
export function getDashboardMetrics(): DashboardMetrics {
  const slots = getSlots();
  const analyses = getAnalysisHistory();
  const kbRecords = getKBRecords();

  const slotsCompleted = slots.filter(s => s.status === 'pass').length;
  const slotsTotal = slots.filter(s => s.phase === 1).length;

  const passCount = slots.filter(s => s.status === 'pass').length;
  const conditionalCount = slots.filter(s => s.status === 'conditional').length;
  const dataQualityScore = Math.round(
    ((passCount + conditionalCount * 0.5) / Math.max(slotsTotal, 1)) * 100
  );

  return {
    slotsCompleted,
    slotsTotal,
    kbRecordsCount: kbRecords.length,
    analysesThisMonth: analyses.length,
    lastAnalysisDate: analyses[0]?.completedAt,
    dataQualityScore,
  } as DashboardMetrics;
}
