import { Outlet, Link } from 'react-router-dom';
import { PipelineStatus } from '../pipeline/PipelineStatus';

export function AppShell() {
  return (
    <div className="flex h-screen bg-[#0D1117] text-white">
      {/* Sidebar Placeholder */}
      <aside className="w-64 bg-[#161B22] border-r border-[#30363D] p-4 flex flex-col">
        <h1 className="text-xl font-bold mb-8 text-[#00FF88]">StockBrief</h1>
        <nav className="flex flex-col gap-2">
          <Link to="/" className="p-2 hover:bg-[#1C2333] rounded">대시보드</Link>
          <Link to="/news" className="p-2 hover:bg-[#1C2333] rounded">뉴스 분석</Link>
          <Link to="/market" className="p-2 hover:bg-[#1C2333] rounded">시세 분석</Link>
          <Link to="/global" className="p-2 hover:bg-[#1C2333] rounded">한미 연계 분석</Link>
          <Link to="/backtest" className="p-2 hover:bg-[#1C2333] rounded">백테스팅</Link>
          <Link to="/report" className="p-2 hover:bg-[#1C2333] rounded">리포트 미리보기</Link>
          <Link to="/analysis" className="p-2 hover:bg-[#1C2333] rounded">섹터 종합 분석</Link>
        </nav>
      </aside>
      
      {/* Main Content Placeholder */}
      <main className="flex-1 overflow-auto bg-[#0D1117] text-[#C9D1D9]">
        <header className="flex items-center justify-end p-4 border-b border-[#30363D] bg-[#161B22]">
          <PipelineStatus />
        </header>
        <div className="p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
