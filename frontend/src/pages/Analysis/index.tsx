import { useEffect, useMemo } from 'react';
import { useAnalysisStore } from '../../store/useAnalysisStore';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'text-[#FF3B3B]',
  negative: 'text-[#3B8BFF]',
  neutral:  'text-[#8B949E]',
};
const SENTIMENT_ARROW: Record<string, string> = {
  positive: '▲',
  negative: '▼',
  neutral:  '—',
};

export default function Analysis() {
  const { data, isLoading, error, fetchAnalysisData } = useAnalysisStore();

  useEffect(() => {
    fetchAnalysisData();
  }, [fetchAnalysisData]);

  const usScoreMap = useMemo(() => {
    const map: Record<string, { score: number; sentiment: string }> = {};
    data?.us_ranking.forEach(u => { map[u.sector] = { score: u.score, sentiment: u.sentiment }; });
    return map;
  }, [data]);

  // Sectors with strong signal in both Korea and US
  const concordantSectors = useMemo(() => {
    if (!data) return [];
    return data.records.filter(r => {
      const us = usScoreMap[r.sector];
      return r.news_score >= 5 && us && us.score >= 5;
    }).sort((a, b) => b.news_score - a.news_score);
  }, [data, usScoreMap]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">섹터 종합 분석</h2>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">섹터 종합 분석</h2>
        <Card><EmptyState description={error || '데이터를 불러올 수 없습니다.'} /></Card>
      </div>
    );
  }

  const recommended = data.records.filter(r => r.recommendation);
  const date = data.records[0]?.date ?? '';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">📊 섹터 종합 분석</h2>
        {date && <span className="text-sm text-[#8B949E]">{date} 기준</span>}
      </div>

      {/* AI 추천 섹터 */}
      {recommended.length > 0 && (
        <Card className="border-[#00FF88]/30">
          <CardHeader>
            <CardTitle className="text-[#00FF88]">✅ AI 추천 섹터</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 flex-wrap">
              {recommended.map(r => (
                <div key={r.sector} className="flex flex-col items-center gap-1 bg-[#1C2333] px-4 py-3 rounded-lg border border-[#00FF88]/20">
                  <span className="font-bold text-white">{r.sector}</span>
                  <span className="text-2xl font-mono text-[#00FF88]">{r.total_score.toFixed(1)}</span>
                  <span className="text-xs text-[#8B949E]">신뢰도 {(r.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 한미 동반 주목 */}
      {concordantSectors.length > 0 && (
        <Card className="border-[#FFD700]/30">
          <CardHeader>
            <CardTitle className="text-[#FFD700]">🌐 한미 동반 주목 섹터</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-[#8B949E] mb-3">한국·미국 모두 뉴스 점수 5점 이상인 섹터</p>
            <div className="flex gap-3 flex-wrap">
              {concordantSectors.map(r => {
                const us = usScoreMap[r.sector]!;
                return (
                  <div key={r.sector} className="bg-[#1C2333] px-4 py-3 rounded-lg border border-[#FFD700]/20 min-w-[120px]">
                    <div className="font-bold text-white text-sm mb-2">{r.sector}</div>
                    <div className="flex gap-4 text-xs">
                      <div>
                        <div className="text-[#8B949E]">🇰🇷 한국</div>
                        <div className="font-mono text-[#FF3B3B] font-bold">{r.news_score.toFixed(1)}</div>
                      </div>
                      <div>
                        <div className="text-[#8B949E]">🇺🇸 미국</div>
                        <div className={`font-mono font-bold ${SENTIMENT_COLOR[us.sentiment]}`}>{us.score.toFixed(1)}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 한국 섹터별 점수 상세 */}
        <Card>
          <CardHeader>
            <CardTitle>🇰🇷 한국 섹터별 점수 상세</CardTitle>
          </CardHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>섹터</TableHead>
                <TableHead className="text-right">뉴스</TableHead>
                <TableHead className="text-right">거래대금%</TableHead>
                <TableHead className="text-right">추세</TableHead>
                <TableHead className="text-right">종합</TableHead>
                <TableHead className="text-center">추천</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.records.map(row => (
                <TableRow key={row.sector} className={row.recommendation ? 'bg-[#00FF88]/5' : ''}>
                  <TableCell className="font-medium">{row.sector}</TableCell>
                  <TableCell className="text-right font-mono">{row.news_score.toFixed(1)}</TableCell>
                  <TableCell className="text-right font-mono">{row.volume_score.toFixed(1)}</TableCell>
                  <TableCell className="text-right font-mono">{row.trend_score}</TableCell>
                  <TableCell className="text-right font-mono font-bold text-[#00FF88]">{row.total_score.toFixed(1)}</TableCell>
                  <TableCell className="text-center">
                    {row.recommendation
                      ? <Badge variant="positive">추천</Badge>
                      : <Badge variant="neutral">-</Badge>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>

        {/* 미국 섹터 뉴스 랭킹 */}
        <Card>
          <CardHeader>
            <CardTitle>🇺🇸 미국 섹터 뉴스 랭킹</CardTitle>
          </CardHeader>
          {data.us_ranking.length === 0 ? (
            <CardContent>
              <EmptyState description="미국 섹터 데이터가 없습니다." />
            </CardContent>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>섹터</TableHead>
                  <TableHead className="text-right">뉴스 점수</TableHead>
                  <TableHead className="text-center">방향</TableHead>
                  <TableHead className="text-center">한국 비교</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.us_ranking.map(row => {
                  const kr = data.records.find(r => r.sector === row.sector);
                  const diff = kr ? row.score - kr.news_score : null;
                  return (
                    <TableRow key={row.sector}>
                      <TableCell className="font-medium">{row.sector}</TableCell>
                      <TableCell className="text-right font-mono font-bold">{row.score.toFixed(1)}</TableCell>
                      <TableCell className={`text-center font-bold ${SENTIMENT_COLOR[row.sentiment]}`}>
                        {SENTIMENT_ARROW[row.sentiment]}
                      </TableCell>
                      <TableCell className="text-center text-xs font-mono">
                        {diff === null ? (
                          <span className="text-[#8B949E]">KR 없음</span>
                        ) : diff > 0.5 ? (
                          <span className="text-[#FF3B3B]">US +{diff.toFixed(1)}</span>
                        ) : diff < -0.5 ? (
                          <span className="text-[#3B8BFF]">KR +{Math.abs(diff).toFixed(1)}</span>
                        ) : (
                          <span className="text-[#8B949E]">유사</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  );
}
