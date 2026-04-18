import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { useAnalysisStore } from '../store';
import type { GeoJSON } from '../types/index';

export const useAnalysis = () => {
  const queryClient = useQueryClient();
  const { currentAnalysis, setAnalysis, assessmentType, personasRequested } = useAnalysisStore();
  const [pollingId, setPollingId] = useState<string | null>(null);

  // Fetch analysis result with polling
  const { data: analysis, isLoading: isFetching } = useQuery({
    queryKey: ['analysis', pollingId],
    queryFn: () => apiService.getAnalysis(pollingId!),
    enabled: !!pollingId,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      if (!data) return 3000;
      const status = data?.status;
      if (status === 'complete' || status === 'failed') {
        setAnalysis(data);
        setPollingId(null);
        return false;
      }
      return status === 'queued' || status === 'processing' ? 3000 : false;
    },
  });

  // Run new analysis
  const { mutate: runAnalysis, isPending: isRunning } = useMutation({
    mutationFn: (params: {
      aoi_geom: GeoJSON.Polygon;
      assessment_type: string;
      personas_requested: string[];
    }) => apiService.runAnalysis(params),
    onSuccess: (data: any) => {
      setPollingId(data.analysis_id);
      queryClient.invalidateQueries({ queryKey: ['analysis-history'] });
    },
  });

  // Fetch analysis history
  const { data: history, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['analysis-history'],
    queryFn: () => apiService.getAnalysisHistory({ page: 1, limit: 20 }),
  });

  const startAnalysis = useCallback(
    (aoiGeom: GeoJSON.Polygon) => {
      runAnalysis({
        aoi_geom: aoiGeom,
        assessment_type: assessmentType,
        personas_requested: personasRequested,
      });
    },
    [runAnalysis, assessmentType, personasRequested]
  );

  return {
    analysis: analysis || currentAnalysis,
    history: (history as any)?.items || [],
    isRunning,
    isFetching,
    isLoadingHistory,
    isPolling: !!pollingId,
    startAnalysis,
    pollStatus: setPollingId,
  };
};
