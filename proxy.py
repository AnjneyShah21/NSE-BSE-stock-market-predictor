"""
NSE Pattern Intelligence — Yahoo Finance Proxy + YouTube Live Streams
======================================================================
Run:
    pip install fastapi uvicorn requests yt-dlp edge-tts
    python proxy.py --port 8080

TTS: Uses Microsoft Edge TTS (edge-tts) — completely free, no API key needed.
     Voices: hi-IN-SwaraNeural (Hindi), en-IN-NeerjaNeural (English)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests, time, subprocess, sys, json, os, asyncio
from typing import Optional

app = FastAPI(title="NSE Pattern Intelligence Proxy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── AI Provider Config ────────────────────────────────────────────────────────
# Priority order: whichever key is set gets used first.
# Set ONE of these environment variables before starting:
#
#   Groq  (FREE - recommended): https://console.groq.com/keys
#     Windows:  set GROQ_API_KEY=gsk_...
#     Mac/Linux: export GROQ_API_KEY=gsk_...
#
#   Gemini (FREE): https://aistudio.google.com/app/apikey
#     Windows:  set GEMINI_API_KEY=AIza...
#     Mac/Linux: export GEMINI_API_KEY=AIza...
#
#   Anthropic (Paid): https://console.anthropic.com/
#     Windows:  set ANTHROPIC_API_KEY=sk-ant-...
#     Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...
#
# Or just pass key in the request body as {"api_key": "...", "provider": "groq"}

GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# ── Edge TTS Voice Config ─────────────────────────────────────────────────────
# Free Microsoft neural voices — no API key needed
# Override via env vars if desired:
#   export EDGE_TTS_VOICE_EN=en-IN-NeerjaNeural
#   export EDGE_TTS_VOICE_HI=hi-IN-SwaraNeural
EDGE_TTS_VOICE_EN = os.environ.get("EDGE_TTS_VOICE_EN", "en-IN-NeerjaNeural")   # Indian English, female
EDGE_TTS_VOICE_HI = os.environ.get("EDGE_TTS_VOICE_HI", "hi-IN-SwaraNeural")   # Hindi, female
# Other good options:
#   en-IN-PrabhatNeural  — Indian English, male
#   hi-IN-MadhurNeural   — Hindi, male
#   en-US-AriaNeural     — US English, female

def detect_provider():
    if GROQ_API_KEY:      return "groq"
    if GEMINI_API_KEY:    return "gemini"
    if ANTHROPIC_API_KEY: return "anthropic"
    return None

@app.post("/ai")
async def ai_proxy(request: Request):
    """
    Universal AI proxy — supports Groq (free), Gemini (free), Anthropic (paid).
    Browser sends same OpenAI-style body: {model, messages, system, max_tokens}
    Proxy adapts and forwards to whichever provider's key is configured.
    """
    body = await request.json()

    # Allow per-request provider override via body
    provider  = body.pop("provider", None) or detect_provider()
    api_key   = body.pop("api_key",  None)

    if not provider:
        raise HTTPException(status_code=500, detail=(
            "No AI API key configured. Set one of:\n"
            "  GROQ_API_KEY      (free) → https://console.groq.com/keys\n"
            "  GEMINI_API_KEY    (free) → https://aistudio.google.com/app/apikey\n"
            "  ANTHROPIC_API_KEY (paid) → https://console.anthropic.com/"
        ))

    messages   = body.get("messages", [])
    system_msg = body.get("system", "")
    max_tokens = body.get("max_tokens", 1000)

    # ── Groq (free, OpenAI-compatible) ──────────────────────────────────────
    if provider == "groq":
        key = api_key or GROQ_API_KEY
        groq_messages = []
        if system_msg:
            groq_messages.append({"role": "system", "content": system_msg})
        groq_messages.extend(messages)

        # Try models in order — Groq deprecates models periodically
        GROQ_MODELS = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

        last_error = None
        for model_name in GROQ_MODELS:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model":       model_name,
                        "messages":    groq_messages,
                        "max_tokens":  max_tokens,
                        "temperature": 0.7,
                    },
                    timeout=30,
                )
                if r.status_code == 404 or (r.status_code == 400 and "model" in r.text.lower()):
                    last_error = f"Model {model_name} not available"
                    continue  # try next model
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return {"content": [{"type": "text", "text": text}], "provider": "groq", "model": model_name}
            except requests.HTTPError as e:
                last_error = str(e)
                if r.status_code in (401, 403):
                    raise HTTPException(status_code=401, detail="Invalid Groq API key. Get a free key at console.groq.com/keys")
                continue
            except Exception as e:
                last_error = str(e)
                continue

        raise HTTPException(status_code=502, detail=f"All Groq models failed. Last error: {last_error}")

    # ── Gemini (free) ────────────────────────────────────────────────────────
    elif provider == "gemini":
        key = api_key or GEMINI_API_KEY
        # Build Gemini content format
        gemini_parts = []
        if system_msg:
            gemini_parts.append({"text": system_msg + "\n\n"})
        for m in messages:
            gemini_parts.append({"text": m["content"]})
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": gemini_parts}], "generationConfig": {"maxOutputTokens": max_tokens}},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"content": [{"type": "text", "text": text}], "provider": "gemini"}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini error: {str(e)}")

    # ── Anthropic (paid) ─────────────────────────────────────────────────────
    elif provider == "anthropic":
        key = api_key or ANTHROPIC_API_KEY
        payload = {k: v for k, v in body.items() if k not in ("provider", "api_key")}
        if system_msg and "system" not in payload:
            payload["system"] = system_msg
        if "model" not in payload:
            payload["model"] = "claude-sonnet-4-20250514"
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Anthropic error: {str(e)}")

    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


from fastapi.responses import StreamingResponse
import io

@app.post("/tts")
async def text_to_speech(request: Request):
    """
    Edge TTS proxy — Microsoft neural voices, completely free, no API key.
    Body: { "text": "...", "lang": "en" | "hi" }
    Returns: audio/mpeg stream
    """
    try:
        import edge_tts
    except ImportError:
        raise HTTPException(status_code=500, detail=(
            "edge-tts not installed. Run: pip install edge-tts"
        ))

    body = await request.json()
    text = body.get("text", "").strip()
    lang = body.get("lang", "en")

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    # Limit text length
    text = text[:800]

    voice = EDGE_TTS_VOICE_HI if lang == "hi" else EDGE_TTS_VOICE_EN

    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        audio_bytes = b"".join(audio_chunks)
        if not audio_bytes:
            raise HTTPException(status_code=502, detail="Edge TTS returned empty audio")
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_bytes))}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Edge TTS error: {str(e)}")

@app.get("/tts/voices")
async def list_voices():
    """List all available Edge TTS voices."""
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        return {"voices": [{"name": v["Name"], "gender": v["Gender"], "locale": v["Locale"]} for v in voices]}
    except ImportError:
        raise HTTPException(status_code=500, detail="edge-tts not installed. Run: pip install edge-tts")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/ai/status")
def ai_status():
    """Check which AI provider is configured."""
    provider = detect_provider()
    return {
        "provider": provider or "none",
        "groq_configured":      bool(GROQ_API_KEY),
        "gemini_configured":    bool(GEMINI_API_KEY),
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "ready": provider is not None,
    }

@app.get("/groq/models")
def groq_models():
    """List currently available Groq models (useful for debugging)."""
    key = GROQ_API_KEY
    if not key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY not set")
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
        return {"models": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ── AMFI NAV proxy ────────────────────────────────────────────────────────────
@app.get("/amfi-nav")
def amfi_nav():
    """Fetches all MF NAVs from AMFI India server-side (bypasses browser CORS)."""
    try:
        r = requests.get(
            "https://www.amfiindia.com/spages/NAVAll.txt",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        r.raise_for_status()
        funds = []
        for line in r.text.splitlines():
            parts = line.split(";")
            if len(parts) >= 6 and parts[0].strip().isdigit():
                try:
                    nav_float = float(parts[4].strip())
                    if nav_float > 0:
                        funds.append({
                            "schemeCode": parts[0].strip(),
                            "isin":       parts[1].strip(),
                            "schemeName": parts[3].strip(),
                            "nav":        nav_float,
                            "date":       parts[5].strip(),
                        })
                except ValueError:
                    pass
        return {"funds": funds, "count": len(funds)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AMFI fetch error: {str(e)}")

YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com",
}

TF_MAP = {
    "1d": ("5m","1d"), "1w": ("60m","5d"), "1m": ("1d","1mo"),
    "3m": ("1d","3mo"), "6m": ("1d","6mo"), "1y": ("1wk","1y"),
}

MARKET_KEYWORDS = [
    "market", "nifty", "sensex", "stock", "share", "trading", "trade",
    "opening bell", "closing bell", "bull", "bear", "indices", "index",
    "bse", "nse", "economy", "finance", "business", "money", "invest",
    "ipo", "earnings", "results", "commodity", "gold", "crude", "rupee",
    "rate", "rbi", "budget", "gdp", "inflation", "rally", "crash",
    "bazaar", "paisa", "nivesh", "profit", "technical analysis",
    "pre-market", "pre market", "post market", "live market",
    "opening", "closing", "midcap", "smallcap", "largecap",
    "खुलावट", "बाजार", "शेयर", "निफ्टी", "सेंसेक्स",
]

LIVE_CHANNELS = [
    {"label": "ET Now",       "url": "https://www.youtube.com/@ETNow",      "desc": "Economic Times — Business & Markets"},
    {"label": "CNBC TV18",    "url": "https://www.youtube.com/@CNBC-TV18",  "desc": "India's #1 Business News"},
    {"label": "Zee Business", "url": "https://www.youtube.com/@ZeeBusiness", "desc": "Live Markets & Finance"},
    {"label": "NDTV Profit",  "url": "https://www.youtube.com/@NDTVProfit",  "desc": "Business, Stocks & Economy"},
    {"label": "CNBC Awaaz",   "url": "https://www.youtube.com/@CNBCAwaaz",  "desc": "Hindi Business News"},
    {"label": "DD News",      "url": "https://www.youtube.com/@DDNewslive",  "desc": "Doordarshan Business News"},
]

_cache: dict = {}
CACHE_TTL = 300

def _ytdlp_available():
    try:
        return subprocess.run(["yt-dlp","--version"], capture_output=True, timeout=5).returncode == 0
    except: return False

def _is_market(title: str) -> bool:
    return any(k in title.lower() for k in MARKET_KEYWORDS)

def _check_embeddable(video_id: str) -> bool:
    """
    Check if a YouTube video actually allows embedding by fetching
    the oEmbed endpoint — if it returns data, embedding is allowed.
    If it returns 401/403/404, embedding is blocked.
    """
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        r = requests.get(url, timeout=8)
        return r.status_code == 200
    except:
        return False

def _get_video_details(video_id: str) -> dict:
    """
    Use yt-dlp to get full details of a single video including
    is_live, title, and most importantly: embeddable flag.
    """
    try:
        result = subprocess.run([
            "yt-dlp",
            "--dump-json",
            "--no-warnings",
            "--quiet",
            "--skip-download",
            f"https://www.youtube.com/watch?v={video_id}",
        ], capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "id":         data.get("id", video_id),
                "title":      data.get("title", ""),
                "is_live":    data.get("is_live", False),
                "embeddable": not data.get("age_limit", 0) and data.get("playability_status") != "LOGIN_REQUIRED",
            }
    except Exception as e:
        print(f"[detail] {video_id}: {e}", file=sys.stderr)
    return {"id": video_id, "title": "", "is_live": False, "embeddable": False}

def _ytdlp_list(url: str, limit=25) -> list[dict]:
    """List videos from a channel URL using yt-dlp flat playlist."""
    try:
        result = subprocess.run([
            "yt-dlp", "--flat-playlist",
            "--playlist-end", str(limit),
            "--print", "%(id)s\t%(title)s\t%(is_live)s",
            "--no-warnings", "--quiet", url,
        ], capture_output=True, text=True, timeout=35)
        entries = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if parts and len(parts[0]) == 11:
                entries.append({
                    "id":      parts[0].strip(),
                    "title":   parts[1].strip() if len(parts) > 1 else "",
                    "is_live": parts[2].strip() == "True" if len(parts) > 2 else None,
                })
        return entries
    except Exception as e:
        print(f"[list] {url}: {e}", file=sys.stderr)
        return []

def _find_embeddable_market_video(ch: dict) -> tuple[Optional[str], Optional[str], bool, str]:
    """
    Strategy:
    1. Collect candidate videos from /live, /streams, /videos
    2. Sort: live+market > live > market > any
    3. For each candidate (best first), check if it's actually embeddable
    4. Return first embeddable one
    """
    url = ch["url"]
    debug = []
    seen = set()
    candidates = []

    for suffix in ["/live", "/streams", "/videos"]:
        entries = _ytdlp_list(url + suffix, limit=25)
        debug.append(f"{suffix}:{len(entries)}")
        for e in entries:
            if e["id"] not in seen:
                seen.add(e["id"])
                score = 0
                if e.get("is_live"): score += 100
                if _is_market(e.get("title","")): score += 50
                candidates.append({**e, "score": score})

    # Sort best first
    candidates.sort(key=lambda x: x["score"], reverse=True)

    debug.append(f"total_candidates:{len(candidates)}")

    # Check embeddability for top candidates (limit checks to avoid slowness)
    for c in candidates[:10]:
        embeddable = _check_embeddable(c["id"])
        debug.append(f"  [{c['id']}] score={c['score']} embed={embeddable} title={c['title'][:50]}")
        if embeddable:
            return c["id"], c["title"], _is_market(c["title"]), " | ".join(debug)

    debug.append("NO_EMBEDDABLE_FOUND")
    return None, None, False, " | ".join(debug)

def _get(ch: dict, force=False) -> dict:
    key = ch["url"]
    now = time.time()
    c = _cache.get(key, {})
    if not force and c.get("video_id") and (now - c.get("fetched_at", 0)) < CACHE_TTL:
        return c
    vid, title, is_market, dbg = _find_embeddable_market_video(ch)
    result = {
        "video_id":  vid,
        "title":     title or ch["label"],
        "embed_src": f"https://www.youtube.com/embed/{vid}?autoplay=1&rel=0&modestbranding=1" if vid else None,
        "is_market": is_market,
        "debug":     dbg,
        "fetched_at": now,
    }
    _cache[key] = result
    return result

@app.get("/live-streams")
def live_streams():
    channels = []
    for ch in LIVE_CHANNELS:
        i = _get(ch)
        channels.append({
            "label": ch["label"], "desc": ch["desc"],
            "video_id": i["video_id"], "title": i["title"],
            "embed_src": i["embed_src"], "is_market": i["is_market"],
            "live": i["video_id"] is not None,
        })
    return {"channels": channels, "ytdlp_ok": _ytdlp_available(), "fetched_at": int(time.time())}

@app.get("/live-streams/refresh")
def refresh():
    _cache.clear()
    return live_streams()

@app.get("/live-streams/debug")
def debug_streams():
    _cache.clear()
    channels = []
    for ch in LIVE_CHANNELS:
        i = _get(ch, force=True)
        channels.append({"label": ch["label"], **i})
    return {"ytdlp_available": _ytdlp_available(), "channels": channels}

@app.get("/quote/{symbol}")
def get_quote(symbol: str, tf: str = "1w"):
    symbol = symbol.upper().strip()
    # Support both NSE (.NS) and BSE (.BO) and index symbols (^NSEI etc.)
    if symbol.startswith("^") or symbol.endswith(".NS") or symbol.endswith(".BO"):
        yf_symbol = symbol
    else:
        yf_symbol = f"{symbol}.NS"  # default to NSE
    interval, range_ = TF_MAP.get(tf, ("60m","5d"))
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
           f"?interval={interval}&range={range_}&includePrePost=false&events=div%7Csplit")
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        r.raise_for_status()
    except requests.HTTPError:
        raise HTTPException(status_code=r.status_code, detail=f"Yahoo {r.status_code} for {yf_symbol}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    data = r.json()
    result = data.get("chart",{}).get("result")
    if not result:
        err = data.get("chart",{}).get("error",{})
        raise HTTPException(status_code=404, detail=err.get("description", f"{yf_symbol} not found"))
    res = result[0]; meta = res["meta"]; ts = res.get("timestamp",[])
    q = res["indicators"]["quote"][0]
    def clean(l): return [v if v is not None else 0 for v in l]
    labels = [time.strftime("%H:%M" if tf=="1d" else "%d %b", time.localtime(t+19800)) for t in ts]
    return {
        "symbol": symbol, "fullName": meta.get("longName") or meta.get("shortName", symbol),
        "currency": meta.get("currency","INR"),
        "currentPrice": meta.get("regularMarketPrice", (clean(q.get("close",[])) or [0])[-1]),
        "previousClose": meta.get("chartPreviousClose", meta.get("previousClose",0)),
        "marketState": meta.get("marketState","CLOSED"), "labels": labels,
        "closes": clean(q.get("close",[])), "opens": clean(q.get("open",[])),
        "highs": clean(q.get("high",[])), "lows": clean(q.get("low",[])),
        "volumes": clean(q.get("volume",[])),
    }

@app.get("/health")
def health():
    return {"status": "ok", "ytdlp": _ytdlp_available()}

if __name__ == "__main__":
    import uvicorn, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"Starting on http://{args.host}:{args.port}")
    uvicorn.run("proxy:app", host=args.host, port=args.port, reload=True)