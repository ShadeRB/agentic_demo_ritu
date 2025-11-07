Agentic Multi-Agent System with Gradio UI

A modular **multi-agent demo app** built with **LangChain**, **Gemini API**, and **Gradio** — showcasing how multiple reasoning and API-connected agents can operate from a single unified interface.

 Project Overview

This project demonstrates three intelligent agents wrapped inside a **Gradio UI**:

| Agent | Purpose | Key Features |
|-------|----------|---------------|
| **Calculator** | Performs step-by-step reasoning and math using a ReAct agent. | Clean output, hidden scratchpad, automatic reasoning steps. |
| **Currency Exchange** | Fetches the latest USD ↔ EUR exchange rate. | Uses live API data with simple, natural-language queries. |
| **Stock & Headlines (Gemini)** | Retrieves real-time stock prices and latest financial headlines. | Combines **Gemini LLM**, **Stooq/Yahoo Finance**, and **Google News RSS**. |
 Tech Stack

- **Python 3.10+**
- **LangChain** for agent orchestration  
- **Google Gemini (Gemini 2.0-Flash)** via `langchain_google_genai`
- **Gradio** for interactive UI
- **dotenv** for secure API key management
- **subprocess** to launch multiple agents seamlessly

🖥️ How to Run

1️⃣ Clone the repository
bash
git clone https://github.com/ShadeRB/agentic_demo_ritu.git
cd agentic_demo_ritu


### 2️⃣ Create a virtual environment

`bash
conda create -n gemini_agent python=3.10 -y
conda activate gemini_agent


### 3️⃣ Install dependencies

bash
pip install -r requirements.txt


(If you don’t have it yet, install manually:)*

bash
pip install gradio langchain langchain-google-genai python-dotenv yfinance pandas requests

4️⃣ Add your `.env` file

In your project root, create a `.env` file with:

GOOGLE_API_KEY=your_gemini_api_key_here

### 5️⃣ Run the app

bash
python -m agents.gradio_app


Then open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

 🧮 Example Outputs

 Calculator

Final Answer: 64.6875

### Currency Exchange

1 USD = 0.93 EUR

### Stock & Headlines (Gemini)

$188.08
- Nvidia shares dip amid AI market correction – Yahoo Finance
- Nvidia: Now is the time to double down – Seeking Alpha

##  Project Structure

```
agentic_demo_ritu/
│
├── demo.py                        # Entry-point script (CLI)
├── agents/
│   ├── calculator_agent.py        # Calculator reasoning agent
│   ├── agent.py                   # Currency exchange agent
│   ├── langchain_gemini_agent.py  # Stock & Headlines agent
│   └── gradio_app.py              # Gradio UI (multi-agent launcher)
│
├── .env                           # (local only, not pushed)
├── .gitignore
└── README.md


 Security Notes

* Your `.env` file **must not** be pushed to GitHub.
* Ensure `.gitignore` includes:

  ```
  .env
  __pycache__/
  *.pyc
  ```
* Gemini free tier allows limited requests — if you see **quota exceeded**, wait a few minutes or upgrade your plan.


Future Enhancements

* Add **Weather Agent** using Open-Meteo API
* Add **Memory & Context** across user sessions
* Support **Agent Tabs View** in Gradio UI
* Integrate **LangGraph** for visualization of reasoning steps

Author

Rituparna Bera (Ritu)

> *This project demonstrates how real-world automation, LLMs, and data APIs can merge into a clean, user-friendly AI system — a hands-on showcase of practical AI engineering and digital product leadership.*
