"""
美股相关公开数据聚合 API。

- 宏观：pyfredapi → FRED（有 FRED_API_KEY 走官方 API；否则降级为 FRED 官网公开 graph CSV）
- 行情：yfinance（雅虎财经，非官方，仅供展示）
- SEC：data.sec.gov 官方 JSON（需合规 User-Agent）
- 资讯：NewsAPI（可选）+ 自选 RSS（feedparser，须遵守来源 ToS）

Stock Analysis Engine / sec-edgar Python 包 / news-please 为独立重型项目，本站以本模块为轻量整合层；
说明见前端「开源与合规」页签。
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from .config import (
    ALPHA_VANTAGE_API_KEY,
    FRED_API_KEY,
    FINNHUB_API_KEY,
    NEWSAPI_KEY,
    NEWS_RSS_BUILTIN_URLS,
    NEWS_RSS_URLS,
    SEC_HTTP_USER_AGENT,
    effective_news_rss_urls,
)

_log = logging.getLogger("meiguwang.us_market")

router = APIRouter(prefix="/us", tags=["us-market"])

_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z.\-]{0,14}$")
_SERIES_RE = re.compile(r"^[A-Z0-9_+.\-]{1,64}$")

_sec_ticker_map: Optional[dict[str, str]] = None
_sec_ticker_loaded_ts: float = 0.0
_SEC_TICKER_TTL = 86400 * 1  # 24h


def _sec_headers() -> dict[str, str]:
    return {
        "User-Agent": SEC_HTTP_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json,text/plain,*/*",
    }


def _load_sec_ticker_to_cik() -> dict[str, str]:
    global _sec_ticker_map, _sec_ticker_loaded_ts
    import time

    now = time.time()
    if _sec_ticker_map and (now - _sec_ticker_loaded_ts) < _SEC_TICKER_TTL:
        return _sec_ticker_map

    url = "https://www.sec.gov/files/company_tickers.json"
    with httpx.Client(timeout=45.0, headers=_sec_headers()) as client:
        r = client.get(url)
        r.raise_for_status()
        raw = r.json()

    m: dict[str, str] = {}
    for v in raw.values():
        if not isinstance(v, dict):
            continue
        t = v.get("ticker")
        cik = v.get("cik_str")
        if t and cik is not None:
            m[str(t).upper()] = str(int(cik)).zfill(10)

    _sec_ticker_map = m
    _sec_ticker_loaded_ts = now
    _log.info("SEC company_tickers 已缓存: %d 条", len(m))
    return m


def _cik_int_from_padded(cik: str) -> int:
    return int(cik.lstrip("0") or "0")


def _sec_filing_url(cik_int: int, accession: str, primary_doc: str) -> str:
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{primary_doc}"


def _fred_csv_headers() -> dict[str, str]:
    return {
        "User-Agent": SEC_HTTP_USER_AGENT,
        "Accept": "text/csv,*/*",
    }


def _fred_series_csv_fallback(series_id: str, limit: int) -> dict[str, Any]:
    """无 API Key 时使用 FRED 官网公开 graph CSV（无需注册；元数据较少，请勿高频请求）。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    with httpx.Client(timeout=45.0, headers=_fred_csv_headers()) as client:
        r = client.get(url)
        r.raise_for_status()
    text = r.text.strip()
    if text.startswith("<!") or "observation_date" not in text.split("\n", 1)[0]:
        raise HTTPException(
            404,
            f"未找到序列 {series_id}，或 FRED 未提供该序列的 CSV 导出。",
        )

    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 2:
        raise HTTPException(502, "FRED CSV 格式异常")

    parsed: list[tuple[str, str]] = []
    for row in reader:
        if len(row) < 2:
            continue
        date_s, val_s = row[0].strip(), row[1].strip()
        if not date_s:
            continue
        parsed.append((date_s, val_s))

    parsed.sort(key=lambda x: x[0], reverse=True)
    lim = min(max(limit, 1), 500)
    observations: list[dict[str, str]] = []
    for date_s, val_s in parsed[:lim]:
        observations.append(
            {"date": date_s[:10] if len(date_s) >= 10 else date_s, "value": val_s}
        )

    return {
        "series_id": series_id,
        # 公开 CSV 无 API 元数据；标题仅序列 ID，由前端展示「公开 CSV」标签
        "title": series_id,
        "units": "",
        "frequency": "",
        "observations": observations,
        "source": "FRED graph CSV (public, no API key)",
        "fred_url": f"https://fred.stlouisfed.org/series/{series_id}",
        "fred_via": "public_csv",
    }


def _fred_series_sync(series_id: str, limit: int) -> dict[str, Any]:
    lim = min(max(limit, 1), 500)
    if FRED_API_KEY:
        from pyfredapi import get_series, get_series_info

        key = FRED_API_KEY
        info = get_series_info(series_id, api_key=key)
        df = get_series(
            series_id,
            api_key=key,
            sort_order="desc",
            limit=lim,
        )
        rows: list[dict[str, str]] = []
        if df is not None and not getattr(df, "empty", True):
            for _, row in df.iterrows():
                d, val = row["date"], row["value"]
                rows.append(
                    {
                        "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
                        "value": ""
                        if val is None or (isinstance(val, float) and str(val) == "nan")
                        else str(val),
                    }
                )

        return {
            "series_id": series_id,
            "title": info.title,
            "units": info.units_short or info.units,
            "frequency": info.frequency_short or info.frequency,
            "observations": rows,
            "source": "FRED / pyfredapi",
            "fred_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "fred_via": "api",
        }

    return _fred_series_csv_fallback(series_id, lim)


def _yfinance_quote_sync(ticker: str) -> dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info or {}
    hist = t.history(period="3mo", interval="1d")
    closes: list[dict[str, Any]] = []
    if hist is not None and not hist.empty:
        tail = hist.tail(60)
        for idx, row in tail.iterrows():
            ts = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
            closes.append({"date": str(ts)[:10], "close": float(row["Close"]) if row["Close"] == row["Close"] else None})

    return {
        "ticker": ticker.upper(),
        "name": info.get("shortName") or info.get("longName") or ticker.upper(),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "quote_type": info.get("quoteType"),
        "regular_market_price": info.get("regularMarketPrice") or info.get("currentPrice"),
        "regular_market_previous_close": info.get("regularMarketPreviousClose") or info.get("previousClose"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "trailing_pe": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "history": closes,
        "source": "Yahoo Finance / yfinance（非官方接口，仅供参考）",
        "disclaimer": "行情与基本面来自第三方聚合，不构成投资建议。",
    }


def _sec_filings_sync(ticker: str, limit: int) -> dict[str, Any]:
    t = ticker.strip().upper()
    tickers = _load_sec_ticker_to_cik()
    cik = tickers.get(t)
    if not cik:
        raise HTTPException(404, f"未在 SEC company_tickers 中找到股票代码：{t}")

    cik_int = _cik_int_from_padded(cik)
    sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    with httpx.Client(timeout=45.0, headers=_sec_headers()) as client:
        r = client.get(sub_url)
        r.raise_for_status()
        data = r.json()

    name = (data.get("name") or t)[:200]
    recent = (data.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    docs = recent.get("primaryDocument") or []

    n = min(limit, len(forms), len(dates), len(accs), len(docs))
    n = max(0, n)
    out: list[dict[str, str]] = []
    for i in range(n):
        acc = accs[i]
        doc = docs[i] if i < len(docs) else ""
        out.append(
            {
                "form": str(forms[i]),
                "filing_date": str(dates[i]),
                "accession": str(acc),
                "document_url": _sec_filing_url(cik_int, str(acc), str(doc)) if doc else "",
            }
        )

    return {
        "ticker": t,
        "cik": cik,
        "company_name": name,
        "filings": out,
        "source": "SEC EDGAR（data.sec.gov 官方 JSON）",
        "browse_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=exclude&count=40",
    }


def _news_merge_sync() -> dict[str, Any]:
    items: list[dict[str, str]] = []
    errors: list[str] = []

    if NEWSAPI_KEY:
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": "us",
                "category": "business",
                "pageSize": 20,
                "apiKey": NEWSAPI_KEY,
            }
            with httpx.Client(timeout=25.0) as client:
                r = client.get(url, params=params)
                r.raise_for_status()
                body = r.json()
            for a in body.get("articles") or []:
                items.append(
                    {
                        "title": (a.get("title") or "")[:300],
                        "source": ((a.get("source") or {}).get("name") or "NewsAPI")[:120],
                        "url": a.get("url") or "",
                        "published_at": a.get("publishedAt") or "",
                        "via": "NewsAPI",
                    }
                )
        except Exception as e:
            _log.warning("NewsAPI 请求失败: %s", e)
            errors.append(f"NewsAPI: {e}")

    rss_urls = effective_news_rss_urls()
    if rss_urls:
        try:
            import feedparser
        except ImportError:
            errors.append("feedparser 未安装")
        else:
            for feed_url in rss_urls:
                try:
                    with httpx.Client(timeout=25.0, headers=_sec_headers()) as client:
                        rr = client.get(feed_url)
                        rr.raise_for_status()
                    parsed = feedparser.parse(rr.text)
                    src_title = (parsed.feed.get("title") or feed_url)[:120]
                    builtin = feed_url in NEWS_RSS_BUILTIN_URLS
                    via = "RSS · SEC Press" if builtin else "RSS"
                    for ent in (parsed.entries or [])[:10]:
                        link = ent.get("link") or ""
                        title = (ent.get("title") or "")[:300]
                        pub = ent.get("published") or ent.get("updated") or ""
                        if title or link:
                            items.append(
                                {
                                    "title": title,
                                    "source": src_title,
                                    "url": link,
                                    "published_at": pub,
                                    "via": via,
                                }
                            )
                except Exception as e:
                    _log.warning("RSS 失败 %s: %s", feed_url, e)
                    errors.append(f"RSS {feed_url}: {e}")

    return {
        "items": items[:40],
        "count": len(items),
        "errors": errors,
        "hint": "资讯须遵守各来源版权与 robots/ToS；证券级新闻流建议使用付费数据商。",
    }


@router.get("/meta")
def us_meta():
    """前端用于展示能力开关（不含密钥）。"""
    rss_eff = effective_news_rss_urls()
    rss_builtin = bool(
        not NEWS_RSS_URLS
        and not NEWSAPI_KEY
        and bool(NEWS_RSS_BUILTIN_URLS)
    )
    return {
        "fred_api_key_configured": bool(FRED_API_KEY),
        "fred_public_csv_fallback": not bool(FRED_API_KEY),
        "fred_configured": bool(FRED_API_KEY),
        "newsapi_configured": bool(NEWSAPI_KEY),
        "rss_feed_count": len(NEWS_RSS_URLS),
        "rss_effective_count": len(rss_eff),
        "rss_builtin_active": rss_builtin,
        "yfinance": True,
        "sec_json": True,
    }


@router.get("/fred/series")
async def us_fred_series(
    series_id: str = Query(..., description="FRED series id，如 UNRATE、CPIAUCSL"),
    limit: int = Query(60, ge=1, le=500),
):
    sid = series_id.strip().upper()
    if not _SERIES_RE.match(sid):
        raise HTTPException(400, "series_id 格式无效")
    try:
        return await asyncio.to_thread(_fred_series_sync, sid, limit)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("FRED 拉取失败")
        raise HTTPException(502, f"FRED 数据暂不可用: {e}") from e


@router.get("/quote")
async def us_quote(ticker: str = Query(..., min_length=1, max_length=16)):
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(400, "股票代码格式无效")
    try:
        return await asyncio.to_thread(_yfinance_quote_sync, t)
    except Exception as e:
        _log.exception("yfinance 失败")
        raise HTTPException(502, f"行情暂不可用: {e}") from e


@router.get("/sec/filings")
async def us_sec_filings(
    ticker: str = Query(..., min_length=1, max_length=16),
    limit: int = Query(20, ge=1, le=80),
):
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(400, "股票代码格式无效")
    try:
        return await asyncio.to_thread(_sec_filings_sync, t, limit)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("SEC 拉取失败")
        raise HTTPException(502, f"SEC 数据暂不可用: {e}") from e


@router.get("/news")
async def us_news():
    try:
        return await asyncio.to_thread(_news_merge_sync)
    except Exception as e:
        _log.exception("资讯聚合失败")
        raise HTTPException(502, str(e)) from e


def _av_news_time_ts(s: Optional[str]) -> float:
    if not s or len(s) < 15:
        return 0.0
    try:
        dt = datetime.strptime(s[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def _research_company_news_sync(ticker: str, limit: int) -> dict[str, Any]:
    """聚合 Finnhub + Alpha Vantage 免费层公司相关新闻（需各自官网注册 API Key）。"""
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(400, "股票代码格式无效")

    lim = min(max(limit, 1), 60)
    raw_items: list[dict[str, Any]] = []
    errors: list[str] = []

    if FINNHUB_API_KEY:
        try:
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=120)
            u = "https://finnhub.io/api/v1/company-news"
            params = {
                "symbol": t,
                "from": start.isoformat(),
                "to": end.isoformat(),
                "token": FINNHUB_API_KEY,
            }
            with httpx.Client(timeout=35.0) as client:
                r = client.get(u, params=params)
                if r.status_code == 403:
                    errors.append("Finnhub: 403，请检查 FINNHUB_API_KEY")
                else:
                    r.raise_for_status()
                    data = r.json()
                    if isinstance(data, list):
                        for row in data:
                            if not isinstance(row, dict):
                                continue
                            ts = float(row.get("datetime") or 0)
                            raw_items.append(
                                {
                                    "title": (row.get("headline") or "")[:400],
                                    "summary": (row.get("summary") or "")[:800],
                                    "url": row.get("url") or "",
                                    "source": (row.get("source") or "Finnhub")[:120],
                                    "published_ts": ts,
                                    "published_at": (
                                        datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                                            "%Y-%m-%d %H:%M UTC"
                                        )
                                        if ts
                                        else ""
                                    ),
                                    "via": "Finnhub",
                                }
                            )
                    elif isinstance(data, dict) and data.get("error"):
                        errors.append(f"Finnhub: {data.get('error')}")
        except Exception as e:
            _log.warning("Finnhub company-news failed: %s", e)
            errors.append(f"Finnhub: {e}")

    if ALPHA_VANTAGE_API_KEY:
        try:
            u = "https://www.alphavantage.co/query"
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": t,
                "limit": str(min(100, max(lim * 2, 25))),
                "apikey": ALPHA_VANTAGE_API_KEY,
            }
            with httpx.Client(timeout=45.0) as client:
                r = client.get(u, params=params)
                r.raise_for_status()
                body = r.json()
            if body.get("Note"):
                errors.append(f"Alpha Vantage: {body['Note']}")
            elif body.get("Information"):
                errors.append(f"Alpha Vantage: {body['Information']}")
            elif isinstance(body.get("feed"), list):
                for row in body["feed"]:
                    if not isinstance(row, dict):
                        continue
                    tp = row.get("time_published") or ""
                    ts = _av_news_time_ts(tp)
                    tit = row.get("title") or ""
                    if not tit.strip():
                        tit = (row.get("summary") or "")[:200]
                    raw_items.append(
                        {
                            "title": tit[:400],
                            "summary": (row.get("summary") or "")[:800],
                            "url": row.get("url") or "",
                            "source": (row.get("source") or "Alpha Vantage")[:120],
                            "published_ts": ts,
                            "published_at": tp,
                            "via": "Alpha Vantage",
                        }
                    )
        except Exception as e:
            _log.warning("Alpha Vantage news failed: %s", e)
            errors.append(f"Alpha Vantage: {e}")

    raw_items.sort(key=lambda x: x.get("published_ts") or 0, reverse=True)
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for it in raw_items:
        key = (it.get("url") or "").strip() or f"t:{it.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append({k: v for k, v in it.items() if k != "published_ts"})
        if len(merged) >= lim:
            break

    hints: list[str] = []
    if not FINNHUB_API_KEY and not ALPHA_VANTAGE_API_KEY:
        hints.append(
            "Finnhub（免费注册）：https://finnhub.io/register → 设置环境变量 FINNHUB_API_KEY（公司新闻推荐）"
        )
        hints.append(
            "Alpha Vantage（免费有日限额）：https://www.alphavantage.co/support/#api-key → ALPHA_VANTAGE_API_KEY"
        )

    return {
        "ticker": t,
        "items": merged,
        "finnhub_configured": bool(FINNHUB_API_KEY),
        "alphavantage_configured": bool(ALPHA_VANTAGE_API_KEY),
        "errors": errors,
        "setup_hints": hints,
    }


@router.get("/research/company-news")
async def us_research_company_news(
    ticker: str = Query(..., min_length=1, max_length=16),
    limit: int = Query(35, ge=1, le=60),
):
    try:
        return await asyncio.to_thread(_research_company_news_sync, ticker, limit)
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("投研资讯聚合失败")
        raise HTTPException(502, str(e)) from e


@router.get("/research/status")
def us_research_status():
    return {
        "finnhub_configured": bool(FINNHUB_API_KEY),
        "alphavantage_configured": bool(ALPHA_VANTAGE_API_KEY),
    }
