import { useEffect } from 'react';
import { useAnalysisStore } from '../../store/useAnalysisStore';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/ui/Table';

export default function Analysis() {
  const { data, isLoading, error, fetchAnalysisData } = useAnalysisStore();

  useEffect(() => {
    fetchAnalysisData();
  }, [fetchAnalysisData]);

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

  const recommended = data.filter((r) => r.recommendation);
  const date = data[0]?.date ?? '';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">📊 섹터 종합 분석</h2>
        {date && <span className="text-sm text-[#8B949E]">{date} 기준</span>}
      </div>

      {recommended.length > 0 && (
        <Card className="border-[#00FF88]/30">
          <CardHeader>
            <CardTitle className="text-[#00FF88]">✅ AI 추천 섹터</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 flex-wrap">
              {recommended.map((r) => (
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

      <Card>
        <CardHeader>
          <CardTitle>섹터별 점수 상세</CardTitle>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>섹터</TableHead>
              <TableHead className="text-right">뉴스 점수</TableHead>
              <TableHead className="text-right">거래대금 비중</TableHead>
              <TableHead className="text-right">추세 점수</TableHead>
              <TableHead className="text-right">종합 점수</TableHead>
              <TableHead className="text-center">추천</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => (
              <TableRow key={row.sector} className={row.recommendation ? 'bg-[#00FF88]/5' : ''}>
                <TableCell className="font-medium">{row.sector}</TableCell>
                <TableCell className="text-right font-mono">{row.news_score.toFixed(1)}</TableCell>
                <TableCell className="text-right font-mono">{row.volume_score.toFixed(1)}%</TableCell>
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
    </div>
  );
}
