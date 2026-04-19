/**
 * api.ts — unified API interface.
 *
 * Delegates to localEngine (fully client-side localStorage implementation).
 * When VITE_API_URL is set, real HTTP calls can be re-enabled by swapping
 * the implementation below.
 */

import * as engine from './localEngine';
import type {
  User,
  LoginRequest,
  LoginResponse,
  DatasetSlot,
  DatasetSlotCode,
  DatasetUpload,
  QAReport,
  Analysis,
  AnalysisRequest,
  KnowledgeBaseRecord,
  Report,
  DashboardMetrics,
} from '../types/index';

class APIService {
  // =========================================================================
  // AUTH
  // =========================================================================
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return engine.login(credentials);
  }

  async getMe(): Promise<User> {
    const user = engine.getStoredUser();
    if (!user) throw new Error('Not authenticated');
    return user;
  }

  async refresh(_token: string) {
    return { accessToken: `local-token-${Date.now()}` };
  }

  async logout(): Promise<void> {
    // nothing to do locally
  }

  // =========================================================================
  // DATASETS
  // =========================================================================
  async getSlots(): Promise<DatasetSlot[]> {
    return engine.getSlots();
  }

  async getSlot(code: string): Promise<DatasetSlot> {
    const slot = engine.getSlots().find(s => s.code === code);
    if (!slot) throw new Error(`Slot ${code} not found`);
    return slot;
  }

  async uploadFile(
    slotCode: string,
    file: File,
    onProgress?: (p: number) => void
  ): Promise<DatasetUpload> {
    const { upload } = await engine.processUpload(
      slotCode as DatasetSlotCode,
      file,
      onProgress ?? (() => {})
    );
    return upload;
  }

  async getQAStatus(uploadId: string): Promise<QAReport> {
    const reports = (engine as unknown as {
      getQAReport?: (id: string) => QAReport | null;
    }).getQAReport?.(uploadId);
    if (!reports) throw new Error('QA report not found');
    return reports;
  }

  async getUploadQAReport(uploadId: string): Promise<QAReport> {
    return this.getQAStatus(uploadId);
  }

  async applyFieldMapping(
    _uploadId: string,
    _mappings: unknown
  ): Promise<{ success: boolean; message: string }> {
    return { success: true, message: 'Field mapping applied' };
  }

  async applyCrsSelection(
    _uploadId: string,
    _crs: unknown
  ): Promise<{ success: boolean; message: string }> {
    return { success: true, message: 'CRS applied' };
  }

  async deleteUpload(_uploadId: string): Promise<void> { /* no-op for now */ }
  async deleteSlot(_slotCode: string): Promise<void> { /* no-op for now */ }

  // =========================================================================
  // ANALYSIS
  // =========================================================================
  async runAnalysis(request: AnalysisRequest): Promise<Analysis> {
    return engine.runAnalysis(request);
  }

  async getAnalysis(analysisId: string): Promise<Analysis> {
    const found = engine.getAnalysisHistory().find(a => a.id === analysisId);
    if (!found) throw new Error('Analysis not found');
    return found;
  }

  async listAnalyses(_limit = 20, _offset = 0): Promise<Analysis[]> {
    return engine.getAnalysisHistory();
  }

  async getAnalysisHistoryList(): Promise<Analysis[]> {
    return engine.getAnalysisHistory();
  }

  async getAnalysisHistory(_params?: unknown): Promise<Analysis[]> {
    return engine.getAnalysisHistory();
  }

  async shareAnalysis(_id: string, _emails: string[]): Promise<void> { /* no-op */ }
  async getSharedAnalysis(_token: string): Promise<Analysis> {
    const all = engine.getAnalysisHistory();
    if (!all[0]) throw new Error('No analysis found');
    return all[0];
  }

  // =========================================================================
  // DOCUMENTS
  // =========================================================================
  async uploadDocument(_file: File): Promise<{ documentId: string }> {
    return { documentId: `doc-${Date.now()}` };
  }

  async getExtractions(_documentId: string): Promise<unknown[]> {
    return [];
  }

  async confirmExtraction(_id: string, _approved: boolean): Promise<void> { /* no-op */ }

  // =========================================================================
  // KNOWLEDGE BASE
  // =========================================================================
  async queryKnowledgeBase(
    bbox?: [number, number, number, number],
    theme?: string
  ): Promise<KnowledgeBaseRecord[]> {
    return engine.getKBRecords(bbox, theme);
  }

  async getKBRecord(recordId: string): Promise<KnowledgeBaseRecord> {
    const found = engine.getKBRecords().find(r => r.id === recordId);
    if (!found) throw new Error('KB record not found');
    return found;
  }

  async createKBRecord(record: Partial<KnowledgeBaseRecord>): Promise<KnowledgeBaseRecord> {
    return engine.createKBRecord(record);
  }

  async deleteKBRecord(id: string): Promise<void> {
    engine.deleteKBRecord(id);
  }

  // =========================================================================
  // GEOREFERENCING
  // =========================================================================
  async uploadMapImage(_file: File): Promise<{ mapImageId: string }> {
    return { mapImageId: `mapimg-${Date.now()}` };
  }

  async getGCPs(_mapImageId: string): Promise<unknown[]> { return []; }
  async updateGCPs(_mapImageId: string, _gcps: unknown[]): Promise<void> { /* no-op */ }
  async computeTransformation(_mapImageId: string): Promise<unknown> { return {}; }
  async getDigitisedFeatures(_mapImageId: string): Promise<unknown[]> { return []; }
  async confirmFeatures(_mapImageId: string, _ids: string[]): Promise<{ confirmed: number }> {
    return { confirmed: _ids.length };
  }

  // =========================================================================
  // REPORTS
  // =========================================================================
  async generateReport(analysisId: string, type: string, format: string): Promise<Report> {
    return engine.generateReport(analysisId, type, format);
  }

  async getReport(reportId: string): Promise<Report> {
    const found = engine.getReports().find(r => r.id === reportId);
    if (!found) throw new Error('Report not found');
    return found;
  }

  async downloadReport(reportId: string): Promise<Blob> {
    const report = await this.getReport(reportId);
    engine.downloadReport(report as Report & { htmlContent?: string });
    return new Blob([]);
  }

  async shareReport(_id: string, _emails: string[]): Promise<void> { /* no-op */ }

  // =========================================================================
  // DASHBOARD
  // =========================================================================
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return engine.getDashboardMetrics();
  }

  // =========================================================================
  // ALIASES
  // =========================================================================
  getReports(): Report[] { return engine.getReports(); }

  getDatasetSlots = this.getSlots.bind(this);

  uploadDataset(slotCode: string, file: File): Promise<DatasetUpload> {
    return this.uploadFile(slotCode, file);
  }

  setToken(_token: string): void { /* no-op */ }
  clearToken(): void { /* no-op */ }
}

export const apiService = new APIService();
