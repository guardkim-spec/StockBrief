import logging
from fastapi import FastAPI
from api.middleware.cors import add_cors
from api.routes import dashboard, news, market, global_route, backtest, report, pipeline, analysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="StockBrief API",
    version="2.0.0",
    description="Daily Korean/US stock briefing backend API",
)

add_cors(app)

app.include_router(dashboard.router, prefix="/api")
app.include_router(news.router,      prefix="/api")
app.include_router(market.router,    prefix="/api")
app.include_router(global_route.router, prefix="/api")
app.include_router(backtest.router,  prefix="/api")
app.include_router(report.router,    prefix="/api")
app.include_router(pipeline.router,  prefix="/api")
app.include_router(analysis.router,  prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
