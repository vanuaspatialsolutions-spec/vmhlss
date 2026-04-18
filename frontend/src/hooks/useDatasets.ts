import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { useDatasetStore } from '../store';

export const useDatasets = () => {
  const queryClient = useQueryClient();
  const { setSlots } = useDatasetStore();
  const [activeQAJobs, setActiveQAJobs] = useState<Record<string, boolean>>({});

  // Fetch all slots
  const { data: slots, isLoading: isLoadingSlots } = useQuery({
    queryKey: ['dataset-slots'],
    queryFn: async () => {
      const data = await apiService.getDatasetSlots();
      setSlots(data as any[]);
      return data;
    },
    staleTime: 30_000,
  });

  // Upload file mutation
  const { mutate: uploadFile, isPending: isUploading } = useMutation({
    mutationFn: ({ slotCode, file }: { slotCode: string; file: File }) =>
      apiService.uploadDataset(slotCode, file),
    onSuccess: (data: any) => {
      setActiveQAJobs((prev) => ({ ...prev, [data.upload_id]: true }));
      queryClient.invalidateQueries({ queryKey: ['dataset-slots'] });
    },
  });

  // Poll QA status for an upload
  const useQAStatus = (uploadId: string | null) =>
    useQuery({
      queryKey: ['qa-status', uploadId],
      queryFn: () => apiService.getQAStatus(uploadId!),
      enabled: !!uploadId && activeQAJobs[uploadId],
      refetchInterval: (query) => {
        const data = query.state.data as any;
        if (!data) return 3000;
        const status = data?.qa_status;
        if (status === 'pending') return 3000;
        // QA complete — stop polling
        setActiveQAJobs((prev) => {
          const next = { ...prev };
          delete next[uploadId!];
          return next;
        });
        return false;
      },
    });

  // Apply field mapping
  const { mutate: applyFieldMapping } = useMutation({
    mutationFn: ({ uploadId, mapping }: { uploadId: string; mapping: Record<string, string> }) =>
      apiService.applyFieldMapping(uploadId, mapping),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dataset-slots'] }),
  });

  // Apply CRS selection
  const { mutate: applyCrsSelection } = useMutation({
    mutationFn: ({ uploadId, crs }: { uploadId: string; crs: string }) =>
      apiService.applyCrsSelection(uploadId, crs),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dataset-slots'] }),
  });

  // Delete upload
  const { mutate: deleteUpload } = useMutation({
    mutationFn: (uploadId: string) => apiService.deleteUpload(uploadId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dataset-slots'] }),
  });

  const handleUpload = useCallback(
    (slotCode: string, file: File) => uploadFile({ slotCode, file }),
    [uploadFile]
  );

  return {
    slots: (slots as any[]) || [],
    isLoadingSlots,
    isUploading,
    uploadFile: handleUpload,
    useQAStatus,
    applyFieldMapping,
    applyCrsSelection,
    deleteUpload,
    activeQAJobs,
  };
};
