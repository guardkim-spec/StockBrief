import { useEffect, useState } from 'react';
import { useNewsStore } from '../../store/useNewsStore';
import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/Tabs';

export default function News() {
  const { data, isLoading, error, fetchMarketNews } = useNewsStore();
  const [market, setMarket] = useState<'korea' | 'us'>('korea');

  useEffect(() => {
    // 오늘 날짜로 가정 (Mock 데이터에서는 date를 무시하거나 하드코딩된 걸 반환)
    fetchMarketNews(market, '');
  }, [market, fetchMarketNews]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">뉴스 분석</h2>
      </div>

      <Tabs defaultValue="korea" onValueChange={(val) => setMarket(val as 'korea' | 'us')}>
        <TabsList className="mb-6">
          <TabsTrigger value="korea">🇰🇷 한국 시장</TabsTrigger>
          <TabsTrigger value="us">🇺🇸 미국 시장</TabsTrigger>
        </TabsList>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : error || !data ? (
          <Card>
            <EmptyState description={error || '뉴스를 불러올 수 없습니다.'} />
          </Card>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold border-b border-[#30363D] pb-2">주요 뉴스 목록</h3>
                {(() => {
                  const analyzed = data.items.filter(item => item.sentiment && item.sector && item.sector !== '기타');
                  return analyzed.length === 0 ? (
                    <EmptyState title="뉴스 없음" description="수집된 기사가 없습니다." />
                  ) : (
                    analyzed.map((item) => (
                      <Card key={item.id} className="hover:border-[#8B949E] transition-colors cursor-pointer" onClick={() => window.open(item.url, '_blank')}>
                        <CardContent className="p-4 flex flex-col gap-2">
                          <div className="flex justify-between items-start gap-4">
                            <h4 className="font-medium text-lg leading-snug">{item.title}</h4>
                            <Badge variant={item.sentiment} className="shrink-0">
                              {item.sentiment === 'positive' ? '호재' : item.sentiment === 'negative' ? '악재' : '중립'} ({item.score})
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 text-sm text-[#8B949E]">
                            <span>{item.source}</span>
                            <span>•</span>
                            <span className="font-semibold">{item.sector}</span>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  );
                })()}
              </div>
              
              <div className="space-y-4">
                <h3 className="text-lg font-semibold border-b border-[#30363D] pb-2">섹터별 요약</h3>
                <Card>
                  <CardContent className="p-0">
                    <div className="divide-y divide-[#30363D]">
                      {data.sector_summary.map((summary) => (
                        <div key={summary.sector} className="p-4 flex items-center justify-between">
                          <span className="font-medium">{summary.sector}</span>
                          <div className="flex gap-4 text-sm">
                            <span className="text-[#FF3B3B]">호재 {summary.positive_count}</span>
                            <span className="text-[#3B8BFF]">악재 {summary.negative_count}</span>
                            <span className="text-[#8B949E]">평균 {summary.avg_score.toFixed(1)}점</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )}
      </Tabs>
    </div>
  );
}
