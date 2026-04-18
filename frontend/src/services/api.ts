import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/index';
import type {
  User,
  LoginRequest,
  LoginResponse,
  DatasetSlot,
  DatasetUpload,
  QAReport,
  FieldMapping,
  CRSSelection,
  Analysis,
  AnalysisRequest,
  KnowledgeBaseRecord,
  Report,
  DashboardMetrics,
  GeoreferencingJob,
  GCPCandidate,
  DigitisedFeature,
} from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: add JWT token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = useAuthStore.getState().token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: handle 401 and refresh token
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (refreshToken) {
              const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                refreshToken,
              });

              const { accessToken, refreshToken: newRefreshToken } = response.data.tokens;
              useAuthStore.getState().setToken(accessToken);
              localStorage.setItem('refreshToken', newRefreshToken);

              originalRequest.headers.Authorization = `Bearer ${accessToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            useAuthStore.getState().logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // =========================================================================
  // AUTH ENDPOINTS
  // =========================================================================
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  }

  async refresh(refreshToken: string) {
    const response = await this.client.post('/auth/refresh', { refreshToken });
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  // =========================================================================
  // DATASET ENDPOINTS
  // =========================================================================
  async getSlots(): Promise<DatasetSlot[]> {
    const response = await this.client.get<DatasetSlot[]>('/datasets/slots');
    return response.data;
  }

  async getSlot(code: string): Promise<DatasetSlot> {
    const response = await this.client.get<DatasetSlot>(`/datasets/slots/${code}`);
    return response.data;
  }

  async uploadFile(slotCode: string, file: File): Promise<DatasetUpload> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('slotCode', slotCode);

    const response = await this.client.post<DatasetUpload>('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getQAStatus(uploadId: string): Promise<QAReport> {
    const response = await this.client.get<QAReport>(`/datasets/uploads/${uploadId}/qa-status`);
    return response.data;
  }

  async getUploadQAReport(uploadId: string): Promise<QAReport> {
    const response = await this.client.get<QAReport>(
      `/datasets/uploads/${uploadId}/qa-report`
    );
    return response.data;
  }

  async applyFieldMapping(
    uploadId: string,
    mappings: FieldMapping[] | Record<string, string>
  ): Promise<{ success: boolean; message: string }> {
    const body = Array.isArray(mappings) ? { mappings } : { mappings };
    const response = await this.client.post(
      `/datasets/uploads/${uploadId}/field-mapping`,
      body,
      { validateStatus: () => true }
    );
    return response.data;
  }

  async applyCrsSelection(
    uploadId: string,
    crsSelection: CRSSelection | string
  ): Promise<{ success: boolean; message: string }> {
    const body = typeof crsSelection === 'string' ? { crs: crsSelection } : crsSelection;
    const response = await this.client.post(
      `/datasets/uploads/${uploadId}/crs-selection`,
      body
    );
    return response.data;
  }

  async deleteUpload(uploadId: string): Promise<void> {
    await this.client.delete(`/datasets/uploads/${uploadId}`);
  }

  async deleteSlot(slotCode: string): Promise<void> {
    await this.client.delete(`/datasets/slots/${slotCode}`);
  }

  // =========================================================================
  // ANALYSIS ENDPOINTS
  // =========================================================================
  async runAnalysis(request: AnalysisRequest): Promise<Analysis> {
    const response = await this.client.post<Analysis>('/analysis/run', request);
    return response.data;
  }

  async getAnalysis(analysisId: string): Promise<Analysis> {
    const response = await this.client.get<Analysis>(`/analysis/${analysisId}`);
    return response.data;
  }

  async listAnalyses(limit: number = 20, offset: number = 0): Promise<Analysis[]> {
    const response = await this.client.get<Analysis[]>('/analysis/list', {
      params: { limit, offset },
    });
    return response.data;
  }

  async getAnalysisHistoryList(): Promise<Analysis[]> {
    const response = await this.client.get<Analysis[]>('/analysis/history');
    return response.data;
  }

  async shareAnalysis(analysisId: string, emails: string[]): Promise<void> {
    await this.client.post(`/analysis/${analysisId}/share`, { emails });
  }

  async getSharedAnalysis(shareToken: string): Promise<Analysis> {
    const response = await this.client.get<Analysis>('/analysis/shared', {
      params: { token: shareToken },
    });
    return response.data;
  }

  // =========================================================================
  // DOCUMENT & EXTRACTION ENDPOINTS
  // =========================================================================
  async uploadDocument(file: File): Promise<{ documentId: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<{ documentId: string }>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  async getExtractions(documentId: string): Promise<any[]> {
    const response = await this.client.get<any[]>(`/documents/${documentId}/extractions`);
    return response.data;
  }

  async confirmExtraction(extractionId: string, approved: boolean): Promise<void> {
    await this.client.post(`/extractions/${extractionId}/confirm`, { approved });
  }

  // =========================================================================
  // KNOWLEDGE BASE ENDPOINTS
  // =========================================================================
  async queryKnowledgeBase(
    bbox?: [number, number, number, number],
    theme?: string
  ): Promise<KnowledgeBaseRecord[]> {
    const response = await this.client.get<KnowledgeBaseRecord[]>('/knowledge-base/query', {
      params: { bbox: bbox?.join(','), theme },
    });
    return response.data;
  }

  async getKBRecord(recordId: string): Promise<KnowledgeBaseRecord> {
    const response = await this.client.get<KnowledgeBaseRecord>(
      `/knowledge-base/records/${recordId}`
    );
    return response.data;
  }

  async createKBRecord(record: Partial<KnowledgeBaseRecord>): Promise<KnowledgeBaseRecord> {
    const response = await this.client.post<KnowledgeBaseRecord>('/knowledge-base/records', record);
    return response.data;
  }

  async deleteKBRecord(recordId: string): Promise<void> {
    await this.client.delete(`/knowledge-base/records/${recordId}`);
  }

  // =========================================================================
  // GEOREFERENCING ENDPOINTS
  // =========================================================================
  async uploadMapImage(file: File): Promise<{ mapImageId: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<{ mapImageId: string }>(
      '/georef/upload-map',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  async getGCPs(mapImageId: string): Promise<GCPCandidate[]> {
    const response = await this.client.get<GCPCandidate[]>(`/georef/${mapImageId}/gcps`);
    return response.data;
  }

  async updateGCPs(mapImageId: string, gcps: GCPCandidate[]): Promise<void> {
    await this.client.put(`/georef/${mapImageId}/gcps`, { gcps });
  }

  async computeTransformation(mapImageId: string): Promise<GeoreferencingJob> {
    const response = await this.client.post<GeoreferencingJob>(
      `/georef/${mapImageId}/compute`,
      {}
    );
    return response.data;
  }

  async getDigitisedFeatures(mapImageId: string): Promise<DigitisedFeature[]> {
    const response = await this.client.get<DigitisedFeature[]>(
      `/georef/${mapImageId}/features`
    );
    return response.data;
  }

  async confirmFeatures(
    mapImageId: string,
    featureIds: string[]
  ): Promise<{ confirmed: number }> {
    const response = await this.client.post(`/georef/${mapImageId}/confirm-features`, {
      featureIds,
    });
    return response.data;
  }

  // =========================================================================
  // REPORT ENDPOINTS
  // =========================================================================
  async generateReport(
    analysisId: string,
    type: string,
    format: string
  ): Promise<Report> {
    const response = await this.client.post<Report>('/reports/generate', {
      analysisId,
      type,
      format,
    });
    return response.data;
  }

  async getReport(reportId: string): Promise<Report> {
    const response = await this.client.get<Report>(`/reports/${reportId}`);
    return response.data;
  }

  async downloadReport(reportId: string): Promise<Blob> {
    const response = await this.client.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async shareReport(reportId: string, emails: string[]): Promise<void> {
    await this.client.post(`/reports/${reportId}/share`, { emails });
  }

  // =========================================================================
  // DASHBOARD ENDPOINTS
  // =========================================================================
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await this.client.get<DashboardMetrics>('/dashboard/metrics');
    return response.data;
  }

  // =========================================================================
  // ALIASES — hooks use these method names
  // =========================================================================
  /** Alias for getSlots() */
  getDatasetSlots = this.getSlots.bind(this);

  /** Alias for uploadFile() */
  uploadDataset(slotCode: string, file: File): Promise<DatasetUpload> {
    return this.uploadFile(slotCode, file);
  }

  /** Overload: accept optional pagination params */
  async getAnalysisHistory(params?: { page?: number; limit?: number }): Promise<any> {
    const response = await this.client.get('/analysis/history', { params });
    return response.data;
  }

  // =========================================================================
  // UTILITY METHODS
  // =========================================================================
  setToken(token: string): void {
    this.client.defaults.headers.common.Authorization = `Bearer ${token}`;
  }

  clearToken(): void {
    delete this.client.defaults.headers.common.Authorization;
  }
}

export const apiService = new APIService();
