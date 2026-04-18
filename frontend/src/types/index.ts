// User and Authentication
export interface User {
  id: string;
  email: string;
  name: string;
  organization?: string;
  roles: string[];
  createdAt: string;
  lastLogin: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

// Dataset Management
export type DatasetSlotCode =
  | 'DS-01'
  | 'DS-02'
  | 'DS-03'
  | 'DS-04'
  | 'DS-05'
  | 'DS-06'
  | 'DS-07'
  | 'DS-08'
  | 'DS-09'
  | 'DS-10'
  | 'DS-11'
  | 'DS-12'
  | 'DS-13'
  | 'DS-14';

export type DatasetSlotStatus = 'empty' | 'pass' | 'conditional' | 'failed' | 'auto_fixed';

export interface DatasetSlot {
  code: DatasetSlotCode;
  name: string;
  description: string;
  status: DatasetSlotStatus;
  phase: 1 | 2;
  acceptedFormats: string[];
  minimumStandard: string;
  recommendedSource?: string;
  uploadedBy?: string;
  uploadedAt?: string;
  dataSourceName?: string;
  lastUpdated?: string;
}

export interface DatasetUpload {
  id: string;
  slotCode: DatasetSlotCode;
  fileName: string;
  fileSize: number;
  uploadedAt: string;
  uploadedBy: string;
  status: 'uploading' | 'queued' | 'processing' | 'completed' | 'failed';
  progress?: number;
}

export type QAStageNumber = 1 | 2 | 3 | 4 | 5 | 6;

export type QAStageName =
  | 'Format Validation'
  | 'Geometry Validation'
  | 'Metadata Extraction'
  | 'CRS Detection'
  | 'Field Mapping'
  | 'Final Review';

export type QAStageResult = 'pass' | 'fail' | 'auto_fixed' | 'pending';

export interface QAStage {
  stage: QAStageNumber;
  name: QAStageName;
  result: QAStageResult;
  description: string;
  fixes?: AutoFix[];
}

export interface AutoFix {
  id: string;
  stage: QAStageNumber;
  type: string;
  description: string;
  before: string;
  after: string;
  affectedRows?: number;
}

export interface QAReport {
  uploadId: string;
  slotCode: DatasetSlotCode;
  stages: QAStage[];
  overallResult: QAStageResult;
  completedAt: string;
  fixes: AutoFix[];
}

export interface FieldMapping {
  sourceField: string;
  targetField: string;
  dataType: string;
  sampleValues: string[];
}

export interface CRSSelection {
  detected: string;
  confirmed: string;
  confidence: number;
}

// Analysis and Results
export type AssessmentType = 'development' | 'agriculture' | 'both';
export type SuitabilityClass = 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'NS';

export interface SuitabilityClassInfo {
  class: SuitabilityClass;
  label: string;
  description: string;
  color: string;
  context: 'agriculture' | 'development' | 'both';
}

export interface AnalysisRequest {
  aoi_geom: GeoJSON.Polygon;
  assessment_type: string;
  personas_requested: string[];
  analysis_name?: string;
}

export interface HazardFactor {
  name: string;
  severity: number;
  impact: 'high' | 'medium' | 'low';
}

export interface AnalysisResult {
  cellId: string;
  geometry: GeoJSON.Point;
  suitabilityClass: SuitabilityClass;
  chiScore: number;
  confidence: number;
  topHazards: HazardFactor[];
  assessmentType: AssessmentType;
}

export interface Analysis {
  id: string;
  name: string;
  aoiGeometry: GeoJSON.Polygon;
  assessmentType: AssessmentType;
  personasRequested: string[];
  createdAt: string;
  completedAt?: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  results?: AnalysisResult[];
  resultsSummary?: {
    s1Count: number;
    s2Count: number;
    s3Count: number;
    s4Count: number;
    s5Count: number;
    nsCount: number;
    totalCells: number;
  };
  createdBy: string;
  sharedWith?: string[];
}

// Knowledge Base
export type ExtractionSource = 'document' | 'field_observation' | 'interview' | 'published_research';

export interface ExtractionItem {
  id: string;
  source: ExtractionSource;
  location: {
    lat: number;
    lon: number;
  };
  statement: string;
  theme: string;
  confidence: number;
  linkedDatasets?: DatasetSlotCode[];
  extractedAt: string;
  extractedBy: string;
}

export interface KnowledgeBaseRecord {
  id: string;
  type: 'location_hazard' | 'land_use_pattern' | 'suitability_observation' | 'historical_event';
  geometry: GeoJSON.Point | GeoJSON.Polygon;
  attributes: Record<string, unknown>;
  sources: ExtractionItem[];
  confirmedAt?: string;
  confirmedBy?: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

// Georeferencing
export interface GCPCandidate {
  id: string;
  imageCoord: [number, number];
  worldCoord?: [number, number];
  confidence: number;
  validated: boolean;
}

export interface GeoreferencingJob {
  id: string;
  mapImageId: string;
  gcpCount: number;
  rmse?: number;
  transformation?: {
    type: string;
    parameters: number[];
  };
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
}

export interface DigitisedFeature {
  id: string;
  geometry: GeoJSON.Geometry;
  properties: Record<string, unknown>;
  verified: boolean;
  verifiedBy?: string;
  verifiedAt?: string;
}

// Reports
export type ReportFormat = 'pdf' | 'geojson' | 'csv' | 'html';
export type ReportType =
  | 'suitability_summary'
  | 'hazard_assessment'
  | 'data_quality'
  | 'decision_support'
  | 'technical_analysis';

export interface Report {
  id: string;
  analysisId: string;
  type: ReportType;
  format: ReportFormat;
  title: string;
  description?: string;
  status: 'queued' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  generatedBy: string;
  downloadUrl?: string;
  pageCount?: number;
}

export interface DashboardMetrics {
  slotsCompleted: number;
  slotsTotal: number;
  kbRecordsCount: number;
  lastAnalysisDate?: string;
  analysesThisMonth: number;
  dataQualityScore: number;
}

// Map and Spatial
export namespace GeoJSON {
  export type Position = [number, number] | [number, number, number];

  export interface Point {
    type: 'Point';
    coordinates: Position;
  }

  export interface Polygon {
    type: 'Polygon';
    coordinates: Position[][];
  }

  export interface Feature<G = Geometry, P = Record<string, unknown>> {
    type: 'Feature';
    geometry: G;
    properties: P;
  }

  export interface FeatureCollection<G = Geometry, P = Record<string, unknown>> {
    type: 'FeatureCollection';
    features: Feature<G, P>[];
  }

  export type Geometry = Point | Polygon;
}

export interface MapLayer {
  id: string;
  name: string;
  category: 'hazard' | 'suitability' | 'lulc' | 'admin' | 'kb';
  visible: boolean;
  opacity: number;
  sourceId: string;
  layerId: string;
  description?: string;
}

// API Error
export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

// i18n
export type Language = 'en' | 'bi';

export interface TranslationKeys {
  // Common UI
  'common.loading': string;
  'common.error': string;
  'common.success': string;
  'common.cancel': string;
  'common.save': string;
  'common.delete': string;
  'common.edit': string;
  'common.close': string;
  'common.next': string;
  'common.previous': string;
  'common.export': string;
  'common.import': string;
  'common.download': string;
  'common.upload': string;
  'common.language': string;

  // Workspaces
  'workspace.mapquery': string;
  'workspace.data': string;
  'workspace.documents': string;
  'workspace.georef': string;
  'workspace.reports': string;

  // Suitability Classes
  'suitability.s1.ag': string;
  'suitability.s2.ag': string;
  'suitability.s3.ag': string;
  'suitability.s4.ag': string;
  'suitability.s5.ag': string;
  'suitability.ns.ag': string;
  'suitability.s1.dev': string;
  'suitability.s2.dev': string;
  'suitability.s3.dev': string;
  'suitability.s4.dev': string;
  'suitability.s5.dev': string;
  'suitability.ns.dev': string;

  // Map Query Workspace
  'mapquery.drawarea': string;
  'mapquery.selectarea': string;
  'mapquery.assessmenttype': string;
  'mapquery.development': string;
  'mapquery.agriculture': string;
  'mapquery.both': string;
  'mapquery.personas': string;
  'mapquery.runanalysis': string;
  'mapquery.layers': string;
  'mapquery.hazard': string;
  'mapquery.suitability': string;
  'mapquery.lulc': string;
  'mapquery.boundaries': string;
  'mapquery.knowledge': string;
  'mapquery.chi': string;
  'mapquery.results': string;
  'mapquery.processing': string;
  'mapquery.clickresult': string;
  'mapquery.export': string;

  // Data Dashboard
  'dashboard.slots': string;
  'dashboard.phase1': string;
  'dashboard.phase2': string;
  'dashboard.upload': string;
  'dashboard.status': string;
  'dashboard.formats': string;
  'dashboard.minimum': string;
  'dashboard.recommended': string;
  'dashboard.dragdrop': string;
  'dashboard.qaprocess': string;
  'dashboard.processing': string;
  'dashboard.passed': string;
  'dashboard.failed': string;
  'dashboard.autofixed': string;
  'dashboard.replace': string;
  'dashboard.fixes': string;

  // Status bar
  'status.slots': string;
  'status.kbrecords': string;
  'status.lastanalysis': string;
}
