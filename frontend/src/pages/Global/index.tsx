import { useEffect } from 'react';
import { useGlobalStore } from '../../store/useGlobalStore';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';

export default function Global() {
  const { data, isLoading, error, fetchGlobalData } = useGlobalStore();

  useEffect(() => {
    fetchGlobalData('');
  }, [fetchGlobalData]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">한미 연계 분석</h2>
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">한미 연계 분석</h2>
        <Card>
          <EmptyState description={error || '데이터를 불러올 수 없습니다.'} />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">🌍 한미 연계 분석</h2>
      </div>

      <Card className="border-[#00FF88]/30">
        <CardHeader>
          <CardTitle className="text-[#00FF88] flex items-center gap-2">
            💡 AI 종합 의견
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-lg leading-relaxed text-white">
            {data.gemini_overall_summary}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6">
        {data.linkage_cards.map((card, idx) => (
          <Card key={idx} className="overflow-hidden">
            <div className="bg-[#161B22] border-b border-[#30363D] p-4 flex flex-col md:flex-row items-center gap-4 justify-between">
              <div className="flex items-center gap-4 flex-1">
                <div className="flex flex-col items-center min-w-24">
                  <span className="text-sm text-[#8B949E] mb-1">🇺🇸 미국</span>
                  <Badge variant={card.us_sentiment}>{card.us_sector}</Badge>
                </div>
                
                <div className="flex-1 flex justify-center text-[#8B949E]">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14"></path>
                    <path d="m12 5 7 7-7 7"></path>
                  </svg>
                </div>

                <div className="flex flex-col items-center min-w-24">
                  <span className="text-sm text-[#8B949E] mb-1">🇰🇷 한국 예상</span>
                  <Badge variant={card.predicted_impact}>{card.korea_sector}</Badge>
                </div>
              </div>
              
              <div className="bg-[#1C2333] px-4 py-2 rounded-lg border border-[#30363D] text-center">
                <span className="text-sm text-[#8B949E] block mb-1">영향도</span>
                <span className="font-mono text-[#00FF88] font-bold">{(card.impact_strength * 100).toFixed(0)}%</span>
              </div>
            </div>
            
            <CardContent className="p-6">
              <h4 className="text-lg font-semibold mb-2">{card.summary}</h4>
              <p className="text-[#8B949E] leading-relaxed">
                {card.reasoning}
              </p>
            </CardContent>
          </Card>
        ))}
        {data.linkage_cards.length === 0 && (
          <EmptyState title="연계 분석 데이터 없음" description="오늘은 눈에 띄는 한미 섹터 연계성이 발견되지 않았습니다." />
        )}
      </div>
    </div>
  );
}
