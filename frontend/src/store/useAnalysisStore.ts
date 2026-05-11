import { create } from 'zustand';
import { fetchAnalysis } from '../api/analysis';
import type { AnalysisData } from '../types/analysis';

interface AnalysisState {
  data: AnalysisData | null;
  isLoading: boolean;
  error: string | null;
  fetchAnalysisData: (date?: string) => Promise<void>;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  data: null,
  isLoading: false,
  error: null,
  fetchAnalysisData: async (date) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetchAnalysis(date);
      if (response.ok && response.data) {
        set({ data: response.data as AnalysisData, isLoading: false });
      } else {
        set({ error: response.error || 'Failed to fetch analysis', isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },
}));
