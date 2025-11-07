# gradio_app.py — unified Gradio front-end for your 3 agents (with dynamic inputs)

from pathlib import Path
from dotenv import load_dotenv
import gradio as gr
import subprocess, sys, re

# --- strip ANSI colors from child scripts ---
ANSI = re.compile(r"\x1b\[[0-9;]*m")
def _clean(s: str) -> str:
    return ANSI.sub("", (s or "").strip())

# Load environment (for Gemini key etc.)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

ROOT = Path(__file__).resolve().parents[1]
AGENTS = {
    "Calculator": ROOT / "agents" / "calculator_agent.py",
    "Currency Exchange": ROOT / "agents" / "agent.py",
    "Stock & Headlines (Gemini)": ROOT / "agents" / "langchain_gemini_agent.py",
}

# -------------------- backend run helper --------------------
def run_agent(choice, ticker, max_headlines, freshness):
    """Runs selected agent and returns cleaned stdout/stderr."""
    cmd = [sys.executable]
    if choice == "Calculator":
        cmd += [str(AGENTS["Calculator"])]
    elif choice == "Currency Exchange":
        cmd += [str(AGENTS["Currency Exchange"])]
    elif choice == "Stock & Headlines (Gemini)":
        cmd += [
            str(AGENTS["Stock & Headlines (Gemini)"]),
            "--ticker", ticker or "NVDA",
            "--max", str(max_headlines or 4),
            "--fresh", str(freshness or 1),
        ]
    else:
        return "Unknown agent choice."

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = res.stdout or res.stderr
        return _clean(out)
    except Exception as e:
        return f"Error running agent: {e}"

# -------------------- Gradio UI --------------------
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🤖 Multi-Agent Demo (Calculator • FX • Stocks)")

    with gr.Row():
        agent_choice = gr.Dropdown(
            label="Select Agent",
            choices=list(AGENTS.keys()),
            value="Stock & Headlines (Gemini)",
        )

    with gr.Row():
        # Visible by default for Gemini; hidden for others via callback below
        ticker = gr.Textbox(label="Ticker (for Gemini agent)", value="NVDA", visible=True)
        max_headlines = gr.Slider(label="Max Headlines", minimum=1, maximum=5, step=1, value=4, visible=True)
        freshness = gr.Slider(label="Recency (days)", minimum=1, maximum=7, step=1, value=1, visible=True)

    run_btn = gr.Button("🚀 Run Agent")
    output_box = gr.Textbox(label="Agent Output", lines=20)

    run_btn.click(
        fn=run_agent,
        inputs=[agent_choice, ticker, max_headlines, freshness],
        outputs=output_box,
    )

    # Dynamic hide/show of Gemini-only inputs
    def toggle_inputs(choice):
        show = choice == "Stock & Headlines (Gemini)"
        return gr.update(visible=show), gr.update(visible=show), gr.update(visible=show)

    agent_choice.change(
        fn=toggle_inputs,
        inputs=[agent_choice],
        outputs=[ticker, max_headlines, freshness],
    )

# -------------------- Run --------------------
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
