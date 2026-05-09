# StockBrief v2.0 — 병렬 개발 계획

## Context

StockBrief v2.0은 PRD에 정의된 일일 주식 브리핑 서비스다. 프론트엔드(Antigravity)와 백엔드(Claude)가 동시에 작업하므로 충돌 없이 병렬 개발이 가능하도록 **파일 소유권, API 계약, 분기 전략**을 명확히 정의한다.

---

## 1. 디렉토리 구조 및 파일 소유권

```
StockBrief/
│
├── shared/                          # ❄️ FROZEN — 양팀 공동 확정 후 동결
│   ├── sectors.json                 # 12개 공통 섹터명 (한국어 원본)
│   ├── api-contract.json            # OpenAPI 스타일 계약서
│   └── mock-data/                   # 양팀 공용 목 데이터
│       ├── dashboard.json
│       ├── news.json
│       ├── market.json
│       ├── global.json
│       ├── backtest.json
│       ├── report.json
│       ├── pipeline-status.json
│       └── error/
│           ├── dashboard.json       # ok: false 시나리오
│           └── pipeline-status.json # overall: "failed" 시나리오
│
├── frontend/                        # 🔵 Antigravity 전용 — Claude 팀 접근 금지
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── .env.development             # VITE_USE_MOCK=true
│   ├── .env.staging                 # VITE_USE_MOCK=false (스테이징 URL)
│   ├── .env.production              # VITE_USE_MOCK=false (프로덕션 URL)
│   ├── index.html
│   ├── public/
│   │   └── fonts/                   # Pretendard, Inter 폰트
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── router.tsx               # React Router v6 6개 라우트
│       ├── styles/
│       │   ├── globals.css          # CSS 변수 (PRD §15 색상값)
│       │   └── tokens.ts            # 디자인 토큰 상수
│       ├── types/                   # TS 인터페이스 (API 계약과 1:1 매핑)
│       │   ├── news.ts
│       │   ├── market.ts
│       │   ├── analysis.ts
│       │   ├── backtest.ts
│       │   ├── pipeline.ts
│       │   └── sectors.ts           # shared/sectors.json const import
│       ├── api/
│       │   ├── client.ts            # ⚡ 단일 fetch 진입점 (VITE_USE_MOCK 스위치)
│       │   ├── dashboard.ts
│       │   ├── news.ts
│       │   ├── market.ts
│       │   ├── global.ts
│       │   ├── backtest.ts
│       │   ├── report.ts
│       │   └── pipeline.ts
│       ├── store/                   # Zustand 스토어 (도메인별 1개)
│       │   ├── useDashboardStore.ts
│       │   ├── useNewsStore.ts
│       │   ├── useMarketStore.ts
│       │   ├── useGlobalStore.ts
│       │   ├── useBacktestStore.ts
│       │   ├── useReportStore.ts
│       │   └── usePipelineStore.ts
│       ├── hooks/                   # store + api 래핑 커스텀 훅
│       ├── components/
│       │   ├── layout/              # AppShell, Sidebar, Topbar, PageContainer
│       │   ├── ui/                  # Card, Badge, Skeleton, Table, Tabs, EmptyState
│       │   ├── charts/              # CandlestickChart, SectorBarChart, SectorPieChart, AccuracyLineChart
│       │   └── pipeline/
│       │       └── PipelineStatus.tsx
│       └── pages/
│           ├── Dashboard/           # index.tsx, SectorRankingCard, PieChartCard, AIRecommendationCard
│           ├── News/                # index.tsx, NewsItem, SectorFilter
│           ├── Market/              # index.tsx, Top100Table, CandleSection
│           ├── Global/              # index.tsx
│           ├── Backtest/            # index.tsx, AccuracyTable
│           └── Report/              # index.tsx, ResendButton
│
├── backend/                         # 🔴 Claude 팀 전용 — Antigravity 접근 금지
│   ├── requirements.txt
│   ├── .env.example                 # 환경변수 문서화 (값 없음)
│   ├── config/
│   │   ├── settings.py              # Pydantic BaseSettings (env 읽기)
│   │   ├── sectors.py               # shared/sectors.json 로드 및 타입 정의
│   │   └── schedule.py              # KST 기준 스케줄 상수
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── korea_price.py           # pykrx top-100 (F-03)
│   │   ├── us_price.py              # yfinance top-100 (F-04)
│   │   ├── korea_news.py            # 네이버 RSS (F-01)
│   │   └── us_news.py               # NewsAPI (F-02)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── gemini_client.py         # Gemini API 래퍼 (할당량 초과 대응)
│   │   ├── sector_classifier.py     # 티커/텍스트 → 12개 섹터 매핑
│   │   ├── trend_analyzer.py        # MA 기울기 → 추세 레이블 + 모멘텀 점수 (F-05)
│   │   ├── ai_recommender.py        # 내일 주목 섹터 추천 (F-06)
│   │   └── global_linker.py         # 한미 연계 분석 (F-07)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── sheets_client.py         # Google Sheets (중복 방지 append)
│   │   ├── drive_client.py          # Google Drive 업로드
│   │   └── github_storage.py        # data/YYYY-MM-DD/ JSON 커밋
│   ├── report/
│   │   ├── __init__.py
│   │   ├── chart_builder.py         # matplotlib base64 차트
│   │   ├── html_builder.py          # 이메일 HTML 조립
│   │   └── email_sender.py          # Gmail API (F-08)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                   # FastAPI 앱 팩토리
│   │   ├── routes/
│   │   │   ├── dashboard.py
│   │   │   ├── news.py
│   │   │   ├── market.py
│   │   │   ├── global_route.py
│   │   │   ├── backtest.py
│   │   │   ├── report.py
│   │   │   └── pipeline.py
│   │   └── middleware/
│   │       └── cors.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # 9단계 순서 실행 (retry 포함)
│   │   ├── retry.py                 # @retry(max=3, delay=30) 데코레이터
│   │   └── notifier.py              # 실패 시 Gmail 알림
│   └── tests/
│       ├── unit/
│       │   ├── test_sector_classifier.py
│       │   ├── test_trend_analyzer.py
│       │   ├── test_collectors.py
│       │   └── test_outlier_filter.py
│       └── integration/
│           ├── test_pipeline_order.py
│           └── test_gemini_response.py
│
├── data/                            # 🤖 파이프라인 자동 생성 — 수동 커밋 절대 금지
│   ├── latest.json                  # 최신 대시보드 전체 payload (매일 덮어쓰기)
│   ├── pipeline-status.json         # 파이프라인 진행 상태 (단계마다 업데이트)
│   └── YYYY-MM-DD/                  # 날짜별 폴더
│       ├── korea_price.json
│       ├── us_price.json
│       ├── korea_news.json
│       ├── us_news.json
│       ├── analysis.json
│       ├── backtest.json
│       ├── global.json
│       ├── candle_data.json
│       └── report.html
│
└── .github/
    └── workflows/
        ├── pipeline.yml             # 🔴 Claude 팀 소유 (nightly 파이프라인)
        └── deploy-frontend.yml      # 🔵 Antigravity 소유 (GitHub Pages/Vercel)
```

---

## 2. API 계약 (REST)

**베이스 URL**: `VITE_API_BASE_URL` (로컬: `http://localhost:8000`)

### 공통 응답 봉투

```json
// 성공
{ "ok": true, "date": "2025-05-09", "data": { ... } }

// 에러
{
  "ok": false,
  "error": "PIPELINE_NOT_RUN",
  "message": "오늘 데이터를 준비 중입니다",
  "last_success_date": "2025-05-08"
}
```

### 엔드포인트 목록

| Method | Path | 쿼리 파라미터 | 설명 |
|--------|------|-------------|------|
| GET | `/api/dashboard` | — | 메인 대시보드 전체 데이터 (단일 호출로 부트스트랩) |
| GET | `/api/news` | `market={korea\|us}`, `date` | 뉴스 목록 + 섹터 요약 |
| GET | `/api/market` | `market={korea\|us}`, `date` | Top100 테이블 + 캔들 데이터 |
| GET | `/api/global` | `date` | 한미 연계 분석 카드 목록 |
| GET | `/api/backtest` | `limit=30` | 백테스팅 기록 + 누적 정확도 |
| GET | `/api/report` | `date` | 리포트 HTML + 발송 상태 |
| POST | `/api/report/resend` | body: `{"date": "..."}` | 이메일 재발송 요청 |
| GET | `/api/pipeline/status` | — | 파이프라인 9단계 진행 상태 |

### 핵심 응답 스키마

#### `GET /api/dashboard` → `data`
```json
{
  "last_updated": "2025-05-09T21:00:00+09:00",
  "pipeline_status": "success",
  "ai_recommendation": {
    "sectors": ["반도체", "바이오/헬스케어", "2차전지"],
    "reason": "반도체 섹터는 ...",
    "confidence": 0.82,
    "generated_at": "2025-05-09T20:00:00+09:00"
  },
  "korea_sector_ranking": [
    { "sector": "반도체", "score": 8.2, "sentiment": "positive" }
  ],
  "us_sector_ranking": [
    { "sector": "반도체", "score": 7.9, "sentiment": "positive" }
  ],
  "korea_sector_volume_distribution": [
    { "sector": "반도체", "volume_amount": 9800000000000, "ratio": 0.31 }
  ],
  "us_sector_volume_distribution": [
    { "sector": "IT/소프트웨어", "volume_amount": 45000000000, "ratio": 0.22 }
  ]
}
```

#### `GET /api/news` → `data`
```json
{
  "market": "korea",
  "date": "2025-05-09",
  "items": [
    {
      "id": "abc123",
      "title": "삼성전자, 반도체 신규 투자 발표",
      "url": "https://...",
      "source": "naver",
      "sector": "반도체",
      "sentiment": "positive",
      "score": 8
    }
  ],
  "sector_summary": [
    { "sector": "반도체", "positive_count": 5, "negative_count": 1, "avg_score": 7.8 }
  ]
}
```

#### `GET /api/market` → `data`
```json
{
  "market": "korea",
  "date": "2025-05-09",
  "top100": [
    {
      "rank": 1, "ticker": "005930", "name": "삼성전자",
      "market": "KOSPI", "sector": "반도체",
      "volume_amount": 980000000000, "change_rate": 2.35, "is_outlier": false
    }
  ],
  "candle_data": [
    {
      "sector": "반도체", "ticker": "005930", "name": "삼성전자",
      "trend": "우상향",
      "momentum_score": 8,
      "candles": [
        { "date": "2025-04-11", "open": 71200, "high": 72500, "low": 70800, "close": 72100, "volume": 15000000 }
      ],
      "ma5": [{ "date": "2025-04-15", "value": 71540 }],
      "ma20": [{ "date": "2025-04-30", "value": 70980 }]
    }
  ]
}
```

#### `GET /api/global` → `data`
```json
{
  "date": "2025-05-09",
  "linkage_cards": [
    {
      "us_sector": "반도체", "us_sentiment": "positive", "us_score": 8,
      "korea_sector": "반도체", "predicted_impact": "positive",
      "impact_strength": 0.85,
      "summary": "미국 반도체 강세가 한국 반도체 섹터에 긍정적 영향 예상",
      "reasoning": "NVIDIA 실적 발표 이후 ..."
    }
  ],
  "gemini_overall_summary": "전반적으로 미국 기술 섹터 강세가 다음 날 한국 시장에 영향을 줄 것으로 예상됩니다."
}
```

#### `GET /api/backtest` → `data`
```json
{
  "cumulative_accuracy": 0.67,
  "records": [
    {
      "date": "2025-05-09",
      "recommended_sectors": ["반도체", "바이오/헬스케어", "2차전지"],
      "actual_top_sectors": ["반도체", "조선/방산", "바이오/헬스케어"],
      "accuracy": 0.67,
      "hit_sectors": ["반도체", "바이오/헬스케어"],
      "miss_sectors": ["2차전지"]
    }
  ]
}
```

#### `GET /api/pipeline/status` → `data`
```json
{
  "date": "2025-05-09",
  "overall": "success",
  "steps": [
    { "name": "korea_price",     "status": "success", "ran_at": "2025-05-09T19:02:11+09:00", "duration_sec": 48 },
    { "name": "korea_news",      "status": "success", "ran_at": "2025-05-09T19:11:03+09:00", "duration_sec": 31 },
    { "name": "us_price",        "status": "success", "ran_at": "2025-05-09T19:21:44+09:00", "duration_sec": 52 },
    { "name": "us_news",         "status": "success", "ran_at": "2025-05-09T19:31:09+09:00", "duration_sec": 29 },
    { "name": "gemini_analysis", "status": "success", "ran_at": "2025-05-09T19:41:55+09:00", "duration_sec": 74 },
    { "name": "trend_ai_global", "status": "success", "ran_at": "2025-05-09T20:01:22+09:00", "duration_sec": 118 },
    { "name": "charts_report",   "status": "success", "ran_at": "2025-05-09T20:31:00+09:00", "duration_sec": 95 },
    { "name": "storage",         "status": "success", "ran_at": "2025-05-09T21:00:12+09:00", "duration_sec": 33 },
    { "name": "email",           "status": "success", "ran_at": "2025-05-09T21:30:05+09:00", "duration_sec": 12 }
  ]
}
```

**`status` 값**: `"pending"` | `"running"` | `"success"` | `"failed"` | `"skipped"`  
**`overall` 값**: `"pending"` | `"running"` | `"success"` | `"failed"` | `"holiday"`

---

## 3. 데이터 저장 계약

### GitHub `data/` 디렉토리

- 파이프라인이 각 단계 완료 시 파일 하나씩 생성
- **재실행 시 덮어쓰기** (새 파일 생성 금지 — 프론트가 부분 데이터 읽는 상황 방지)
- `latest.json` = `/api/dashboard` 전체 payload (매일 덮어쓰기)
- 프론트엔드 프로덕션 폴백 URL (FastAPI 서버 없을 때):
  ```
  https://raw.githubusercontent.com/{owner}/{repo}/main/data/latest.json
  https://raw.githubusercontent.com/{owner}/{repo}/main/data/pipeline-status.json
  ```

### Google Sheets — 시트명: `StockBrief_v2`

| 탭 이름 | 컬럼 | 중복 방지 키 | 보관 |
|--------|------|------------|------|
| `korea_price` | date, ticker, name, market, sector, volume_amount, change_rate, rank, is_outlier | date + ticker | 1년 |
| `us_price` | (동일) | date + ticker | 1년 |
| `korea_news` | date, id, title, url, source, sector, sentiment, score | date + id | 1년 |
| `us_news` | (동일) | date + id | 1년 |
| `analysis` | date, sector, news_score, volume_score, trend_score, total_score, recommendation, confidence | date + sector | 무제한 |
| `backtest` | date, recommended_sectors(|구분), actual_top_sectors(|구분), accuracy, hit/miss | date | 무제한 |
| `pipeline_log` | date, step, status, ran_at, duration_sec, error_message | date + step | 90일 |

### Google Drive

```
StockBrief_v2/reports/YYYY-MM/stockbrief_YYYY-MM-DD.html
```

---

## 4. 개발 단계

### Phase 0 — 공통 계약 확정 (Day 1, 양팀 함께 최대 2시간)

> 이 단계만 양팀이 협업. 이후 완전 독립.

- [ ] `shared/sectors.json` 작성 — 12개 섹터명 한국어 원문 확정
- [ ] `shared/mock-data/*.json` 작성 — 백엔드 초안, 프론트 1시간 내 리뷰
- [ ] `shared/api-contract.json` 작성
- [ ] `git commit "chore: freeze shared contracts"`
- [ ] GitHub 브랜치 보호 규칙 설정

**`shared/sectors.json` 내용 (확정 불변):**
```json
{
  "sectors": [
    "반도체", "바이오/헬스케어", "2차전지", "자동차",
    "금융", "에너지", "소비재", "철강/소재",
    "조선/방산", "부동산/건설", "통신/미디어", "IT/소프트웨어"
  ]
}
```
> ⚠️ 이 문자열들은 절대 코드에 하드코딩 금지. 반드시 `shared/sectors.json`에서만 읽어온다.

---

### Phase 1 — 스켈레톤 & 인프라 (Day 1–3)

#### 🔵 Frontend (Antigravity)
| 작업 | 파일 |
|------|------|
| Vite 5 + React 19 + TypeScript 스캐폴딩 | `frontend/` 루트 |
| Tailwind CSS + shadcn/ui 설정 + CSS 변수 (PRD §15) | `tailwind.config.ts`, `globals.css` |
| 디자인 토큰 상수 | `src/styles/tokens.ts` |
| TypeScript 인터페이스 정의 | `src/types/*.ts` |
| fetch 진입점 (VITE_USE_MOCK 스위치) | `src/api/client.ts` |
| AppShell + Sidebar + Topbar | `src/components/layout/` |
| React Router v6 라우트 (6개, lazy-load) | `src/router.tsx` |
| Zustand 스토어 껍데기 (shape만) | `src/store/*.ts` |

#### 🔴 Backend (Claude)
| 작업 | 파일 |
|------|------|
| Python 스캐폴딩 + requirements.txt | `backend/` 루트 |
| Pydantic BaseSettings (env 읽기) | `config/settings.py` |
| sectors.json 로드 | `config/sectors.py` |
| @retry 데코레이터 (max=3, delay=30s) | `pipeline/retry.py` |
| Gmail 실패 알림 | `pipeline/notifier.py` |
| FastAPI 스켈레톤 (mock-data 반환) | `api/app.py` + `api/routes/` |
| GitHub Actions cron 스켈레톤 | `.github/workflows/pipeline.yml` |

---

### Phase 2 — 핵심 데이터 레이어 (Day 4–8)

#### 🔵 Frontend (Antigravity)
| 작업 | 파일 |
|------|------|
| 엔드포인트별 fetch 함수 | `src/api/*.ts` |
| Zustand fetch 액션 (loading/error/data 3-state) | `src/store/*.ts` |
| 커스텀 훅 | `src/hooks/*.ts` |
| UI 프리미티브 (Card, Badge, Skeleton, Table, Tabs, EmptyState) | `src/components/ui/` |
| 대시보드 페이지 (레이아웃 + 목 데이터) | `pages/Dashboard/` |
| 뉴스 페이지 (한국/미국 탭, Skeleton) | `pages/News/` |

#### 🔴 Backend (Claude)
| 작업 | 파일 |
|------|------|
| pykrx top-100 수집 + 이상값 플래그 | `collectors/korea_price.py` |
| yfinance top-100 수집 + 랜덤 딜레이 | `collectors/us_price.py` |
| 네이버 RSS 수집 + URL 중복 제거 | `collectors/korea_news.py` |
| NewsAPI 수집 + URL 중복 제거 | `collectors/us_news.py` |
| 티커/텍스트 → 12개 섹터 매핑 | `analysis/sector_classifier.py` |
| Google Sheets 중복 방지 append | `storage/sheets_client.py` |
| data/YYYY-MM-DD/ JSON 커밋 | `storage/github_storage.py` |
| 단위 테스트 | `tests/unit/` |

---

### Phase 3 — 분석 엔진 & 차트 페이지 (Day 9–14)

#### 🔵 Frontend (Antigravity)
| 작업 | 파일 |
|------|------|
| TradingView 캔들차트 (candles/ma5/ma20 props) | `components/charts/CandlestickChart.tsx` |
| 섹터 바차트, 파이차트, 정확도 라인차트 | `components/charts/` |
| 대시보드 페이지 완성 (4개 섹션 실 훅 연결) | `pages/Dashboard/` |
| 시세 페이지 (Top100 테이블 + 캔들 섹션) | `pages/Market/` |
| 한미 연계 페이지, 백테스팅 페이지 | `pages/Global/`, `pages/Backtest/` |
| PipelineStatus (60초 폴링) | `components/pipeline/PipelineStatus.tsx` |

#### 🔴 Backend (Claude)
| 작업 | 파일 |
|------|------|
| Gemini API 래퍼 (할당량 초과 → 직전 결과 대체) | `analysis/gemini_client.py` |
| MA 기울기 → 추세 레이블 + 모멘텀 점수 | `analysis/trend_analyzer.py` |
| 백테스팅 데이터 포함 AI 추천 | `analysis/ai_recommender.py` |
| 한미 연계 분석 | `analysis/global_linker.py` |
| matplotlib base64 차트 | `report/chart_builder.py` |
| 이메일 HTML 조립 + Gmail API 발송 | `report/html_builder.py`, `report/email_sender.py` |
| 9단계 파이프라인 순서 실행 | `pipeline/orchestrator.py` |
| pipeline.yml: echo → Python 실제 호출 교체 | `.github/workflows/pipeline.yml` |
| 통합 테스트 | `tests/integration/` |

---

### Phase 4 — 통합 & 완성 (Day 15–18)

#### 🔵 Frontend (Antigravity)
| 작업 | 파일 |
|------|------|
| 리포트 페이지 (HTML iframe 미리보기 + 재발송 POST) | `pages/Report/` |
| VITE_USE_MOCK=false 전환, 실 백엔드 연결 | `.env.production` |
| 에러 바운더리 + last_success_date 폴백 UI | `App.tsx` |
| 반응형 768px+ (Tailwind md: 브레이크포인트) | 전 페이지 |
| GitHub Pages/Vercel 배포 워크플로 | `.github/workflows/deploy-frontend.yml` |

#### 🔴 Backend (Claude)
| 작업 | 파일 |
|------|------|
| Google Drive 리포트 업로드 | `storage/drive_client.py` |
| holidays + pytz 공휴일/DST 처리 | `config/settings.py` |
| FastAPI 라우트: mock → 실파일 읽기 전환 | `api/routes/*.py` |
| CORS 설정 (프론트 origin 허용) | `api/middleware/cors.py` |
| 전체 파이프라인 드라이런 (이메일 제외) | `pipeline/orchestrator.py` |
| GitHub Secrets 등록 | Actions 설정 |

---

### Phase 5 — 강화 (Day 19–21)

| 팀 | 작업 |
|----|------|
| Frontend | Lighthouse 감사, 접근성 검토, PRD §15 디자인 QA |
| Backend | 수집기 재시도 검증, Sheets 중복 방지 검증, 실제 파일럿 런 |

---

## 5. 목 데이터 전략

### 프론트엔드 목 스위치 (`src/api/client.ts` 하나에서만 분기)

```
.env.development  →  VITE_USE_MOCK=true   (shared/mock-data/*.json import)
.env.staging      →  VITE_USE_MOCK=false  (VITE_API_BASE_URL=스테이징)
.env.production   →  VITE_USE_MOCK=false  (VITE_API_BASE_URL=프로덕션)
```

어떤 페이지/컴포넌트도 목 데이터를 **직접 import 금지**. 오직 `client.ts`에서만.

### 3가지 URL 우선순위 (`client.ts` 내부)

1. `VITE_USE_MOCK=true` → mock JSON import
2. `VITE_API_BASE_URL` 설정됨 → FastAPI 호출
3. 폴백 → `VITE_GITHUB_RAW_URL` (GitHub raw content 직접 읽기)

### 에러 시나리오 목 (`shared/mock-data/error/`)

- `pipeline-status.json` — `overall: "failed"`, 특정 step `"failed"`
- `dashboard.json` — `ok: false`, `last_success_date` 어제 날짜

---

## 6. 충돌 방지 규칙

### 파일 소유권 — 강제 규칙

| 경로 | 소유자 | 규칙 |
|------|--------|------|
| `frontend/**` | Antigravity만 | Claude 팀 PR 절대 금지 |
| `backend/**` | Claude만 | Antigravity PR 절대 금지 |
| `shared/**` | 동결 | 변경 시 양팀 모두 LGTM 필수 |
| `.github/workflows/pipeline.yml` | Claude만 | — |
| `.github/workflows/deploy-frontend.yml` | Antigravity만 | — |
| `data/**` | 파이프라인 자동 생성 | 수동 커밋 절대 금지 |
| `prd.md` | 읽기 전용 | 양팀 수정 금지 |

### 브랜치 전략

```
main
├── frontend/phase-1-skeleton       (Antigravity)
├── frontend/phase-2-data-layer     (Antigravity)
├── frontend/phase-3-charts         (Antigravity)
├── backend/phase-1-skeleton        (Claude)
├── backend/phase-2-collectors      (Claude)
├── backend/phase-3-analysis        (Claude)
└── integration/phase-4             (양팀 공동)
```

- `frontend/**` 브랜치: Antigravity 리드 승인 필요
- `backend/**` 브랜치: Claude 팀 리드 승인 필요
- `main`: 양팀 모두 승인 필요

### API 계약 변경 프로세스

1. 변경 요청 팀이 `contract-change` 태그 이슈 오픈
2. 양팀 모두 이슈에 `LGTM` 댓글 후 코드 작성 시작
3. `shared/api-contract.json` + `shared/mock-data/` 먼저 동일 커밋으로 업데이트
4. 백엔드 구현 → 프론트엔드 TS 타입 업데이트 → **동시 배포**

### 섹터명 제로 톨러런스

`shared/sectors.json`의 12개 한국어 문자열은 가장 위험한 공유 상태다.  
공백 하나, 반각/전각 차이 하나가 섹터 분류를 무음 오류로 깨뜨린다.

- **백엔드**: `config/sectors.py`에서만 로드, 코드 어디에도 하드코딩 금지
- **프론트엔드**: `src/types/sectors.ts`에서 `as const` import, 어디에도 하드코딩 금지

### 환경변수 소유권

| 변수 | 소유자 | 저장 위치 |
|------|--------|---------|
| `VITE_API_BASE_URL` | Frontend | `frontend/.env.*` |
| `VITE_GITHUB_RAW_URL` | Frontend | `frontend/.env.*` |
| `VITE_USE_MOCK` | Frontend | `frontend/.env.*` |
| `GEMINI_API_KEY` | Backend | GitHub Secrets |
| `GMAIL_OAUTH_TOKEN` | Backend | GitHub Secrets |
| `NEWSAPI_KEY` | Backend | GitHub Secrets |
| `GOOGLE_SHEETS_ID` | Backend | GitHub Secrets |
| `GOOGLE_DRIVE_FOLDER_ID` | Backend | GitHub Secrets |

백엔드 시크릿은 절대 `frontend/`에 존재하지 않는다.

---

## 7. 핵심 파일 (우선순위 순)

| 파일 | 설명 |
|------|------|
| `shared/sectors.json` | Day 1 가장 먼저 확정. 모든 섹터 처리의 원천 |
| `shared/mock-data/dashboard.json` | 프론트엔드 전체 개발 언블록 |
| `frontend/src/api/client.ts` | 목↔실서버 유일한 스위치 포인트 |
| `backend/api/app.py` | FastAPI 진입점, 모든 라우트 마운트 |
| `backend/pipeline/orchestrator.py` | 9단계 파이프라인 순서 제어 |
| `backend/config/sectors.py` | 백엔드 섹터명 단일 공급원 |
| `frontend/src/types/sectors.ts` | 프론트엔드 섹터명 단일 공급원 |

---

## 8. 검증 방법

### 로컬 통합 테스트

```bash
# 백엔드 실행
cd backend && uvicorn api.app:app --reload

# 프론트엔드 실행 (실 백엔드 연결)
cd frontend && VITE_USE_MOCK=false VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

6개 페이지 접속 → 네트워크 탭에서 API 응답 shape이 `shared/api-contract.json`과 일치하는지 확인

### 파이프라인 드라이런

```bash
python -m pipeline.orchestrator --dry-run --date 2025-05-09
```

- `data/2025-05-09/*.json` 파일 생성 확인
- `pipeline-status.json`의 모든 step `"success"` 확인
- 이메일 실제 발송 없이 HTML 파일만 생성

### GitHub Actions 수동 테스트

- `pipeline.yml`에 `workflow_dispatch` 트리거 추가
- Actions 탭 → 수동 실행 → 각 step 로그 + `data/` 파일 생성 확인
