import type { ApiResponse } from '../types/dashboard';

// mock-data dynamically imported
const mocks = {
  dashboard: () => import('../../../shared/mock-data/dashboard.json').then((m) => m.default),
  news: () => import('../../../shared/mock-data/news.json').then((m) => m.default),
  market: () => import('../../../shared/mock-data/market.json').then((m) => m.default),
  global: () => import('../../../shared/mock-data/global.json').then((m) => m.default),
  backtest: () => import('../../../shared/mock-data/backtest.json').then((m) => m.default),
  report: () => import('../../../shared/mock-data/report.json').then((m) => m.default),
  pipeline_status: () => import('../../../shared/mock-data/pipeline-status.json').then((m) => m.default),
  analysis: () => import('../../../shared/mock-data/analysis.json').then((m) => m.default),
};

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function fetchApi<T>(endpoint: keyof typeof mocks, path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  if (USE_MOCK) {
    // Return mock data with artificial delay
    return new Promise((resolve) => {
      setTimeout(async () => {
        const mockData = await mocks[endpoint]();
        resolve(mockData as unknown as ApiResponse<T>);
      }, 500);
    });
  }

  // Real fetch — empty API_BASE_URL means Vite proxy handles routing (relative path)
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
