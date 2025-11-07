import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

load_dotenv()
print("API Key Loaded:", os.getenv("GOOGLE_API_KEY") is not None)

@tool
def calculator(expression: str) -> str:
    """
    Use this tool to evaluate a mathematical expression.
    It can handle addition, mutliplication, subtraction, division and exponents.
    Example: `calculator("2 + 2")` or `calculator('3**4')`
    """
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error evaluating expression: {e}"
    
tools = [calculator]


llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)

template = """
Answer the following questions as best you can. 
You have access to the following tools:
{tools}
Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!
Question: {input}
Thought:{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)

agent = create_react_agent(llm, tools, prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

if __name__ == "__main__":
    print("Starting agent...")

    question = "If a pizza costs $18.75 and I want to buy 3, plus a 15% tip, what is the total cost?"

    result = agent_executor.invoke({"input": question})

    print("Final Answer:", result['output'])

