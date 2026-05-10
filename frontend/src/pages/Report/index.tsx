import { useEffect, useState } from 'react';
import { useReportStore } from '../../store/useReportStore';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { EmptyState } from '../../components/ui/EmptyState';

export default function Report() {
  const { data, isLoading, isResending, error, fetchReportData, triggerResend } = useReportStore();
  const [resendStatus, setResendStatus] = useState<'idle' | 'success' | 'error'>('idle');

  useEffect(() => {
    fetchReportData('');
  }, [fetchReportData]);

  const handleResend = async () => {
    const ok = await triggerResend('');
    setResendStatus(ok ? 'success' : 'error');
    setTimeout(() => setResendStatus('idle'), 3000);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">이메일 리포트 미리보기</h2>
        <Skeleton className="h-96 w-full max-w-3xl mx-auto" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">이메일 리포트 미리보기</h2>
        <Card>
          <EmptyState description={error || '리포트 데이터를 불러올 수 없습니다.'} />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">✉️ 이메일 리포트 미리보기</h2>
        
        <div className="flex items-center gap-4">
          <div className="text-sm">
            {(data.email_sent || data.send_status === 'sent') ? (
              <span className="text-[#00FF88]">✅ 발송 완료 ({new Date(data.sent_at).toLocaleTimeString('ko-KR')})</span>
            ) : (
              <span className="text-[#F59E0B]">⏳ 발송 대기 중</span>
            )}
          </div>
          
          <button
            onClick={handleResend}
            disabled={isResending}
            className={`px-4 py-2 rounded-md font-medium text-sm transition-colors ${
              isResending 
                ? 'bg-[#30363D] text-[#8B949E] cursor-not-allowed'
                : resendStatus === 'success'
                ? 'bg-[#00FF88]/20 text-[#00FF88]'
                : resendStatus === 'error'
                ? 'bg-[#FF3B3B]/20 text-[#FF3B3B]'
                : 'bg-[#1C2333] hover:bg-[#30363D] text-white border border-[#30363D]'
            }`}
          >
            {isResending ? '발송 중...' : resendStatus === 'success' ? '발송 요청 완료!' : resendStatus === 'error' ? '발송 실패' : '수동 재발송'}
          </button>
        </div>
      </div>

      <Card className="max-w-3xl mx-auto bg-white overflow-hidden shadow-lg">
        {/* Render HTML content safely inside an iframe for isolation, or dangerouslySetInnerHTML. 
            For this UI, dangerouslySetInnerHTML is simpler since we control the backend. */}
        <div 
          className="w-full h-full min-h-[600px] bg-white text-black p-0"
          dangerouslySetInnerHTML={{ __html: data.html_content }}
        />
      </Card>
    </div>
  );
}
