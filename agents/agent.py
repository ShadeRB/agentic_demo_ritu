# agents/agent.py — safer ReAct with parse/429 handling

import sys, time, re
from typing import Optional

from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    # If google library is present, we'll gracefully handle rate limits
    from google.api_core.exceptions import ResourceExhausted
except Exception:  # pragma: no cover
    class ResourceExhausted(Exception):
        pass

# -------------------- Tools (toy example: exchange) --------------------

@tool
def ExchangeRateConverter(pair: str) -> str:
    """
    Return a simple spot-like rate string for a pair like "USD EUR".
    Output MUST be '1 USD = 0.93 EUR' (no extra text).
    """
    # Dummy value for demo. Replace with your live source if you like.
    pair = pair.strip().upper().split()
    if len(pair) != 2:
        return "Invalid pair."
    base, quote = pair
    # Hard-coded to match your logs; replace with real lookup if needed
    return f"1 {base} = 0.93 {quote}"

TOOLS = [ExchangeRateConverter]

# -------------------- Prompt (strict ReAct) --------------------

REACT_PROMPT = """
You are a precise assistant that follows the ReAct pattern.

You have tools:
{tools}

Tool names: {tool_names}

Rules:
- If you need information, take exactly ONE Action and wait for its Observation.
- DO NOT write "Final Answer" in the same turn where you take an Action.
- Only when you are completely done (no more Actions needed) output:
  Final Answer: <the concise answer only, no extra narration>

Format strictly:
Thought: <your reasoning>
Action: <one of {tool_names}>
Action Input: <input>
Observation: <tool result>

(repeat Thought/Action/Action Input/Observation as needed)
THEN finish with:
Final Answer: <answer>

IMPORTANT:
- Never include both an Action and Final Answer in the same step.
- Keep the Final Answer to a single line if possible.

Question: {input}

{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(REACT_PROMPT)

# -------------------- LLM & Agent --------------------

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.1,
)

agent = create_react_agent(llm, TOOLS, prompt=prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=False,
    handle_parsing_errors=True,      # don't crash on minor format drift
    return_intermediate_steps=False,
    early_stopping_method="generate",# if stuck, generate a best-effort final
    max_iterations=4,                # keep it tight
)

# -------------------- Helpers --------------------

FINAL_RE = re.compile(r"Final Answer:\s*(.+)", flags=re.S)

def try_extract_final(text: str) -> Optional[str]:
    """Pulls 'Final Answer: ...' from any error blob."""
    m = FINAL_RE.search(text or "")
    if m:
        ans = m.group(1).strip()
        # keep just the first line (your demos expect a single-line answer)
        return ans.splitlines()[0].strip()
    return None

# -------------------- Main --------------------

if __name__ == "__main__":
    q = "What is the exchange rate between USD and EUR?"

    # One retry on 429 with backoff; also salvage Final Answer from parse errors.
    try:
        out = agent_executor.invoke({"input": q})
        print(out.get("output", "").strip())
    except ResourceExhausted:
        print("[rate-limit] Gemini quota hit; waiting 35s and retrying once...", file=sys.stderr)
        time.sleep(35)
        out = agent_executor.invoke({"input": q})
        print(out.get("output", "").strip())
    except Exception as e:
        # If the model produced a Final Answer inside the exception text, surface it.
        salvaged = try_extract_final(str(e))
        if salvaged:
            print(salvaged)
        else:
            # Last resort: show a compact hint and bubble the error message
            print("Error: could not parse a final answer.\nHint: model emitted both an Action and Final Answer in the same step.", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)
