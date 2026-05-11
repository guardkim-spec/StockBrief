export interface AnalysisRecord {
  date: string;
  sector: string;
  news_score: number;
  volume_score: number;
  trend_score: number;
  total_score: number;
  recommendation: boolean;
  confidence: number;
}

export interface UsSectorScore {
  sector: string;
  score: number;
  sentiment: 'positive' | 'negative' | 'neutral';
}

export interface AnalysisData {
  records: AnalysisRecord[];
  us_ranking: UsSectorScore[];
}
