# demo.py — multi-agent launcher with post-formatting for gemini_react

from dotenv import load_dotenv; load_dotenv()

import argparse, subprocess, sys, pathlib, re, json

ROOT = pathlib.Path(__file__).parent
AGENTS = {
    "react_calculator": ROOT / "agents" / "calculator_agent.py",
    "gemini_react":     ROOT / "agents" / "langchain_gemini_agent.py",
    "tool_exchange":    ROOT / "agents" / "agent.py",
}

# ---------- Output formatting helpers (for gemini_react only) ----------

PRICE_RE = re.compile(r"^\$\d[\d,]*\.?\d*$")

def format_guard(out_str: str, max_bullets: int) -> str:
    """
    Enforce:
      - first line is a $price
      - next N bullets in `- Title – host` style (no URLs)
    Applies only to the text that appears after the line '----Final Result----'.
    """
    if not out_str.strip():
        return out_str

    # Find the "Final Result" section if present
    marker = "----Final Result----"
    if marker in out_str:
        head, tail = out_str.split(marker, 1)
        processed_tail = _format_final_block(tail, max_bullets)
        return head + marker + processed_tail
    else:
        # If no marker, best-effort format the whole output
        return _format_final_block(out_str, max_bullets)

def _format_final_block(block: str, max_bullets: int) -> str:
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return "\n\n(No output)\n"

    # 1) keep first valid price line (or first line)
    price = next((l for l in lines if PRICE_RE.match(l)), lines[0])

    # 2) collect bullets
    bullets = []
    for l in lines:
        if l.startswith("- "):
            b = l[2:].strip()
            b = b.replace(" - ", " – ")  # prefer en dash
            b = b.replace("’", "'")      # normalize curly apostrophe
            bullets.append(b)

    if not bullets:
        bullets = ["No recent headlines found."]
    bullets = bullets[:max_bullets]

    final = [price] + [f"- {b}" for b in bullets]
    return "\n" + "\n".join(final) + "\n"

# ---------- Runner ----------

def run_agent(agent_path: pathlib.Path, args_to_pass: list[str], postprocess=False, max_bullets: int = 4):
    """
    Runs the agent as a subprocess. If postprocess=True, applies format_guard to stdout.
    """
    cmd = [sys.executable, str(agent_path), *args_to_pass]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out, err = proc.stdout, proc.stderr

    if postprocess:
        out = format_guard(out, max_bullets)

    # Echo child output/stderr exactly (helpful when debugging)
    if out:
        print(out, end="")
    if err:
        print(err, file=sys.stderr, end="")

    return proc.returncode

def main():
    p = argparse.ArgumentParser(description="Multi-agent demo launcher")
    p.add_argument("--which", choices=AGENTS.keys(), required=True, help="Which demo to run")

    # Optional: pass-through tuning flags for gemini_react
    p.add_argument("--ticker", default=None, help="Ticker for gemini_react (e.g., NVDA)")
    p.add_argument("--max", type=int, default=None, help="Headline count for gemini_react (1..5)")
    p.add_argument("--fresh", type=int, default=None, help="Recency window in days (1..7) for gemini_react")
    p.add_argument("--json", action="store_true", help="Ask gemini_react to also print JSON")
    args = p.parse_args()

    agent_path = AGENTS[args.which]
    child_args: list[str] = []

    # Only gemini_react understands these flags; pass them through if provided.
    if args.which == "gemini_react":
        if args.ticker:
            child_args += ["--ticker", args.ticker]
        if args.max is not None:
            child_args += ["--max", str(args.max)]
        if args.fresh is not None:
            child_args += ["--fresh", str(args.fresh)]
        if args.json:
            child_args += ["--json"]
        # Postprocess final output to keep format tidy
        max_bullets = args.max if (isinstance(args.max, int) and 1 <= args.max <= 5) else 4
        rc = run_agent(agent_path, child_args, postprocess=True, max_bullets=max_bullets)
        sys.exit(rc)

    # Other agents: just run as-is, no postprocessing
    rc = run_agent(agent_path, child_args, postprocess=False)
    sys.exit(rc)

if __name__ == "__main__":
    main()
