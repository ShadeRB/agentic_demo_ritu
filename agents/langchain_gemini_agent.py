# --- load .env from project root
from pathlib import Path
from dotenv import load_dotenv

# Looks for a .env one directory above this file (project root)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

import sys
import re
import argparse
import json
import requests
from io import StringIO
from urllib.parse import urlparse, parse_qs, quote
from xml.etree import ElementTree as ET

# LangChain / LLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent

# -------- runtime-tunable defaults (overridden by CLI) --------
HEADLINE_FRESH_DAYS = 1   # recency window for Google News: when:<d>
HEADLINE_MAX = 4          # number of headlines to return (3–5 recommended)

# ------------------------------ Tools ------------------------------

@tool
def get_stock_price(ticker: str) -> str:
    """Latest price for a ticker (e.g., NVDA). Tries Stooq (with .us) then Yahoo."""
    import pandas as pd
    import yfinance as yf

    if not ticker:
        return "No ticker given."

    t = ticker.strip().upper()
    # Stooq needs '.us' for US tickers, but try both
    candidates = [t.lower(), f"{t.lower()}.us"]

    # 1) Stooq (no key) with timeout + robust read
    for sym in candidates:
        try:
            url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
            resp = requests.get(url, timeout=10)
            if resp.ok and resp.text.strip():
                df = pd.read_csv(StringIO(resp.text))
                if not df.empty and "Close" in df.columns:
                    last = float(df["Close"].iloc[-1])
                    label = sym.upper()
                    return f"The latest price of {t} is ${last:.2f} (Stooq {label})."
        except Exception:
            # try next source
            pass

    # 2) Yahoo Finance fallback (no key)
    try:
        fast = getattr(yf.Ticker(t), "fast_info", None)
        if fast:
            last = getattr(fast, "last_price", None) or (fast.get("last_price") if isinstance(fast, dict) else None)
            if last:
                return f"The latest price of {t} is ${float(last):.2f} (Yahoo)."
        # backup: small historical window
        hist = yf.download(t, period="5d", interval="1d", progress=False)
        if not hist.empty:
            return f"Recent close for {t} is ${float(hist['Close'][-1]):.2f} (Yahoo)."
        return f"No price data returned for {t}. Try later or another ticker."
    except Exception as e:
        return f"Price lookup error for {t}: {e}"


def _unwrap_google_news(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.netloc.endswith("news.google.com"):
            qs = parse_qs(parsed.query)
            if "url" in qs and qs["url"]:
                return qs["url"][0]
    except Exception:
        pass
    return url

def _short_host(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host.startswith("m."):
            host = host[2:]
        return host
    except Exception:
        return url

def _clean_title(s: str) -> str:
    # drop parentheticals like (NASDAQ:NVDA)
    s = re.sub(r"\s*\([^)]+\)", "", s)
    # collapse extra spaces/dashes
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

@tool
def news_headlines(query: str) -> str:
    """Return up to N recent headlines via Google News RSS (no API key), plain lines."""
    try:
        # build query with recency window; localized for Canada/English
        q = f"{query} when:{HEADLINE_FRESH_DAYS}d"
        rss_url = (
            f"https://news.google.com/rss/search?q={quote(q)}"
            f"&hl=en-CA&gl=CA&ceid=CA:en"
        )
        xml = requests.get(rss_url, timeout=15).text
        root = ET.fromstring(xml)
        rows = []
        seen_titles = set()
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            link = _unwrap_google_news(link)
            host = _short_host(link)
            title = _clean_title(title)
            if title and link and title not in seen_titles:
                rows.append(f"{title} | {link} | {host}")
                seen_titles.add(title)
            if len(rows) >= int(HEADLINE_MAX):
                break
        return "\n".join(rows) if rows else "No headlines found."
    except Exception as e:
        return f"Headline fetch error: {e}"

# ------------------------------ LLM / Prompt ------------------------------

# 2) LLM (uses GOOGLE_API_KEY from env; no key handling here)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",   # or "gemini-2.5-flash"
    temperature=0.2,
)

# 3) ReAct prompt (include required vars: tools, tool_names, agent_scratchpad, input)
template = """
You are a precise financial assistant.

You have access to tools:
{tools}

Tool names: {tool_names}

Task:
1) Use tools to get the latest stock price for a ticker.
2) Use tools to fetch 3–5 very recent news headlines.
3) Produce the Final Answer in this exact format:
   - A single line with just the price like: "$123.45"
   - Then 3–5 bullets: "Title – host"

Rules:
- Do NOT copy/paste tool Observations verbatim.
- Headlines tool returns plain lines: "Title | full_link | host".
  • Use only Title and host for the bullets ("Title – host").
  • Do NOT include the raw URLs in the Final Answer.
- If no headlines, write one bullet: "No recent headlines found."
- Keep it concise. No extra commentary.

Follow ReAct:
Thought: ...
Action: one of {tool_names}
Action Input: ...
Observation: ...
(repeat as needed)

When done, output only:
Final Answer:
$<price>
- <Title 1> – <host 1>
- <Title 2> – <host 2>
- <Title 3> – <host 3>

Input question: {input}

{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)

# 4) Agent
tools = [get_stock_price, news_headlines]
agent = create_react_agent(llm, tools, prompt=prompt)

# Tip: keep verbose=False in production to avoid printing chain-of-thought
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    handle_parsing_errors=True,
    return_intermediate_steps=False,
)

# ------------------------------ Output helpers ------------------------------

PRICE_RE = re.compile(r"^\$\d[\d,]*\.?\d*$")

def format_guard(out_str: str, max_bullets: int) -> str:
    """Normalize final output: one price line + up to N bullets, no URLs."""
    lines = [l.strip() for l in (out_str or "").strip().splitlines() if l.strip()]
    if not lines:
        return out_str

    # 1) keep only the first valid price line
    price = next((l for l in lines if PRICE_RE.match(l)), lines[0])

    # 2) collect bullets ("- " prefixed), normalize dash and quotes
    bullets = []
    for l in lines:
        if l.startswith("- "):
            b = l[2:].strip()
            b = b.replace(" - ", " – ")  # en dash
            b = b.replace("’", "'")      # normalize smart quotes
            bullets.append(b)

    # 3) clamp count
    if not bullets:
        bullets = ["No recent headlines found."]
    bullets = bullets[:max_bullets]

    # 4) rebuild
    final = [price] + [f"- {b}" for b in bullets]
    return "\n".join(final)

def to_json(out_str: str) -> str:
    """Convert the clean output to JSON: {'price': '$x', 'headlines': [{title,host}]}"""
    lines = [l.strip() for l in (out_str or "").strip().splitlines() if l.strip()]
    price = lines[0] if lines else ""
    headlines = []
    for l in lines[1:]:
        if l.startswith("- "):
            txt = l[2:].strip()
            if " – " in txt:
                title, host = txt.split(" – ", 1)
            else:
                title, host = txt, ""
            headlines.append({"title": title.strip(), "host": host.strip()})
    return json.dumps({"price": price, "headlines": headlines}, ensure_ascii=False, indent=2)

# ------------------------------ Main ------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="NVDA", help="Ticker symbol to query, e.g., NVDA")
    parser.add_argument("--max", type=int, default=4, help="Max number of headlines (3–5 recommended)")
    parser.add_argument("--fresh", type=int, default=1, help="Recency window in days for headlines (when:<d>)")
    parser.add_argument("--json", action="store_true", help="Also print JSON output")
    args = parser.parse_args()

    # apply CLI overrides for the headlines tool
    HEADLINE_MAX = max(1, min(args.max, 5))          # keep within 1..5
    HEADLINE_FRESH_DAYS = max(1, min(args.fresh, 7)) # keep within 1..7

    # steer the agent with a clear instruction (it still must use tools)
    goal = f"Get {args.ticker} latest price and {HEADLINE_MAX} recent headlines (fresh={HEADLINE_FRESH_DAYS}d)."
    result = agent_executor.invoke({"input": goal})

    print("----Final Result----")
    safe_out = format_guard(result.get("output", ""), HEADLINE_MAX)
    print(safe_out)

    if args.json:
        print(to_json(safe_out))
