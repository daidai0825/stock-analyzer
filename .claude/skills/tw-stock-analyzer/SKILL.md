---
name: tw-stock-analyzer
description: >
  台股與美股分析系統開發 skill。處理 FinMind/yfinance 
  資料擷取、技術指標計算（KD, RSI, MACD, 布林通道）、
  股票篩選、回測引擎開發。當開發股票分析相關功能時自動載入。
---

# 台股美股分析系統開發指引

## 資料來源
- 台股: FinMind API (https://api.finmindtrade.com)
- 美股: yfinance
- 快取策略: Redis, 行情資料 5 分鐘 TTL

## 技術指標標準
所有指標需支援自訂參數，預設值：
- MA: [5, 10, 20, 60, 120, 240]
- RSI: period=14
- MACD: fast=12, slow=26, signal=9
- KD: period=9, smooth_k=3, smooth_d=3
- Bollinger Bands: period=20, std=2

## 回測引擎規範
- 支援初始資金、手續費率（台股 0.1425%）、交易稅（0.3%）
- 輸出指標: 年化報酬率, Sharpe Ratio, Max Drawdown, 勝率
- 績效基準: 與大盤 (TAIEX/SPY) 比較

## 程式碼規範
- 資料處理統一用 pandas DataFrame
- 時間序列用 UTC，顯示時轉換為台北時間
- 所有金額用 Decimal 避免浮點誤差
- 每個 service 都要有對應的 pytest 測試