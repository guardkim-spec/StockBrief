import { fetchApi } from './client';
import type { AnalysisRecord } from '../types/analysis';

export const fetchAnalysis = async (date?: string) => {
  const query = date ? `?date=${date}` : '';
  return fetchApi<AnalysisRecord[]>('analysis', `/api/analysis${query}`);
};
