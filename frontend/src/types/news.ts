import type { Sector } from './sectors';

export interface NewsItem {
  id: string;
  title: string;
  url: string;
  source: string;
  sector: Sector | string;
  sentiment: 'positive' | 'negative' | 'neutral' | '';
  score: number;
  _inferred?: boolean;
}

export interface SectorSummary {
  sector: Sector | string;
  positive_count: number;
  negative_count: number;
  avg_score: number;
  total_count: number;
}

export interface NewsData {
  market: 'korea' | 'us';
  date: string;
  items: NewsItem[];
  sector_summary: SectorSummary[];
}
