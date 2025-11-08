ReadMe **agent scripts**
A modular multi-agent demo app built with LangChain, Gemini API, and Gradio — showcasing how multiple reasoning and API-connected agents can operate from a single unified interface.

Project Overview

This project demonstrates three intelligent agents wrapped inside a Gradio UI:

Agent	Purpose	Key Features
Calculator	Performs step-by-step reasoning and math using a ReAct agent.	Clean output, hidden scratchpad, automatic reasoning steps.
Currency Exchange	Fetches the latest USD ↔ EUR exchange rate.	Uses live API data with simple, natural-language queries.
Stock & Headlines (Gemini)	Retrieves real-time stock prices and latest financial headlines.	Combines Gemini LLM, Stooq/Yahoo Finance, and Google News RSS.




agentic_demo_ritu/
├─ .env
├─ demo.py
├─ 07_1_llm_compiler.ipynb
└─ agents/
   ├─ agent.py                  ← Tool-Calling (Exchange-Rate) agent  
   ├─ calculator_agent.py       ← ReAct calculator agent  
   └─ langchain_gemini_agent.py ← Gemini chat / retrieval agent

###  What each “agent” means

| **agent.py**                  | *Tool-Calling Agent* | Uses the **ExchangeRate API** tool; can look up live USD/EUR or GBP/JPY rates. This is the one printing “setting up env… LLM initialized…”. |
| **calculator_agent.py**       |  *ReAct Math Agent*   | Uses LangChain’s **ReAct** framework to plan and solve basic arithmetic using a simple calculator tool.                                     |
| **langchain_gemini_agent.py** |  *Gemini LLM Agent*   | Connects directly to Google’s **Gemini model (gemini-2.0-flash)** for open-ended reasoning and text generation.                             |

###  Summary

All three are *independent agents* but share:

* The same `.env` file (for API keys)
* The same Python environment (`gemini_agent`)
* The same entry point (`demo.py`) that lets you pick which one to run.

If you run:

bash
python demo.py --which react_calculator

→ runs `calculator_agent.py`

bash
python demo.py --which gemini_react

→ runs `langchain_gemini_agent.py`

bash
python demo.py --which tool_exchange

→ runs `agent.py`

