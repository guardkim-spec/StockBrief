import { useEffect, useState, useMemo } from 'react';
import { useNewsStore } from '../../store/useNewsStore';
import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/Tabs';

const SENTIMENT_LABEL: Record<string, string> = {
  positive: '호재',
  negative: '악재',
  neutral: '중립',
};

function SectorBar({ summary, maxTotal }: { summary: { sector: string; positive_count: number; negative_count: number; avg_score: number; total_count: number }; maxTotal: number }) {
  const { sector, positive_count, negative_count, total_count } = summary;
  const neutral_count = total_count - positive_count - negative_count;
  const barWidth = maxTotal > 0 ? (total_count / maxTotal) * 100 : 0;

  return (
    <div className="flex items-center gap-3 py-2">
      <span className="text-sm font-medium w-28 shrink-0 text-right text-[#E6EDF3]">{sector}</span>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex h-5 rounded overflow-hidden bg-[#161B22]" style={{ width: `${barWidth}%`, minWidth: '4px' }}>
          {positive_count > 0 && (
            <div
              className="h-full bg-[#FF3B3B]"
              style={{ width: `${(positive_count / total_count) * 100}%` }}
            />
          )}
          {neutral_count > 0 && (
            <div
              className="h-full bg-[#3D4450]"
              style={{ width: `${(neutral_count / total_count) * 100}%` }}
            />
          )}
          {negative_count > 0 && (
            <div
              className="h-full bg-[#3B8BFF]"
              style={{ width: `${(negative_count / total_count) * 100}%` }}
            />
          )}
        </div>
        <span className="text-xs text-[#8B949E] shrink-0">{total_count}건</span>
        <div className="hidden sm:flex gap-2 text-xs shrink-0">
          {positive_count > 0 && <span className="text-[#FF3B3B]">호재 {positive_count}</span>}
          {negative_count > 0 && <span className="text-[#3B8BFF]">악재 {negative_count}</span>}
          {neutral_count > 0 && <span className="text-[#8B949E]">중립 {neutral_count}</span>}
        </div>
      </div>
    </div>
  );
}

export default function News() {
  const { data, isLoading, error, fetchMarketNews } = useNewsStore();
  const [market, setMarket] = useState<'korea' | 'us'>('korea');
  const [selectedSector, setSelectedSector] = useState<string>('전체');

  useEffect(() => {
    fetchMarketNews(market, '');
    setSelectedSector('전체');
  }, [market, fetchMarketNews]);

  const filteredItems = useMemo(() => {
    if (!data) return [];
    const withSector = data.items.filter(item => item.sector && item.sector !== '기타');
    if (selectedSector === '전체') return withSector;
    return withSector.filter(item => item.sector === selectedSector);
  }, [data, selectedSector]);

  const maxTotal = useMemo(() => {
    if (!data) return 1;
    return Math.max(...data.sector_summary.map(s => s.total_count), 1);
  }, [data]);

  const sectorCounts = useMemo(() => {
    const map: Record<string, number> = {};
    data?.sector_summary.forEach(s => { map[s.sector] = s.total_count; });
    return map;
  }, [data]);

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
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : error || !data ? (
          <Card>
            <EmptyState description={error || '뉴스를 불러올 수 없습니다.'} />
          </Card>
        ) : (
          <div className="space-y-5">
            {/* Sector distribution overview */}
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-[#8B949E] uppercase tracking-wider">섹터별 현황</h3>
                  <div className="flex gap-3 text-xs text-[#8B949E]">
                    <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm bg-[#FF3B3B]" />호재</span>
                    <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm bg-[#3D4450]" />중립</span>
                    <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm bg-[#3B8BFF]" />악재</span>
                  </div>
                </div>
                <div className="divide-y divide-[#21262D]">
                  {data.sector_summary.length === 0 ? (
                    <p className="text-sm text-[#8B949E] py-4 text-center">수집된 뉴스가 없습니다.</p>
                  ) : (
                    data.sector_summary.map(summary => (
                      <SectorBar key={summary.sector} summary={summary} maxTotal={maxTotal} />
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Sector filter */}
            <div className="flex gap-2 flex-wrap">
              {['전체', ...data.sector_summary.map(s => s.sector)].map(sector => (
                <button
                  key={sector}
                  onClick={() => setSelectedSector(sector)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    selectedSector === sector
                      ? 'bg-[#1F6FEB] text-white'
                      : 'bg-[#21262D] text-[#8B949E] hover:bg-[#30363D] hover:text-[#E6EDF3]'
                  }`}
                >
                  {sector}
                  {sector !== '전체' && sectorCounts[sector] != null && (
                    <span className="ml-1.5 opacity-70">{sectorCounts[sector]}</span>
                  )}
                  {sector === '전체' && (
                    <span className="ml-1.5 opacity-70">{data.items.filter(i => i.sector && i.sector !== '기타').length}</span>
                  )}
                </button>
              ))}
            </div>

            {/* News list */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#8B949E] uppercase tracking-wider">
                  {selectedSector === '전체' ? '전체 뉴스' : `${selectedSector} 뉴스`}
                </h3>
                <span className="text-xs text-[#30363D] bg-[#21262D] px-2 py-0.5 rounded-full">
                  {filteredItems.length}건
                </span>
              </div>

              {filteredItems.length === 0 ? (
                <Card>
                  <EmptyState title="뉴스 없음" description="해당 섹터의 뉴스가 없습니다." />
                </Card>
              ) : (
                filteredItems.map(item => (
                  <Card
                    key={item.id}
                    className="hover:border-[#8B949E] transition-colors cursor-pointer"
                    onClick={() => window.open(item.url, '_blank')}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start gap-4">
                        <h4 className="font-medium text-sm leading-snug text-[#E6EDF3] flex-1">
                          {item.title}
                        </h4>
                        {item.sentiment ? (
                          <Badge variant={item.sentiment as 'positive' | 'negative' | 'neutral'} className="shrink-0">
                            {SENTIMENT_LABEL[item.sentiment] ?? item.sentiment} {item.score > 0 && `(${item.score})`}
                          </Badge>
                        ) : (
                          <span className="shrink-0 text-xs text-[#8B949E] bg-[#21262D] px-2 py-0.5 rounded-md">
                            키워드 분류
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-xs text-[#8B949E]">
                        <span className="font-semibold text-[#58A6FF]">{item.sector}</span>
                        <span>•</span>
                        <span>{item.source}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>
        )}
      </Tabs>
    </div>
  );
}
