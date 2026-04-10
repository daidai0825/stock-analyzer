from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alerts, auth, backtest, portfolios, screener, stocks, watchlists
from app.core.config import settings

app = FastAPI(
    title="Stock Analyzer API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(watchlists.router, prefix="/api/v1/watchlists", tags=["watchlists"])
app.include_router(screener.router, prefix="/api/v1/screener", tags=["screener"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
