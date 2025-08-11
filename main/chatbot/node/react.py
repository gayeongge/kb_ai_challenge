import os
from langchain.agents import create_react_agent, AgentExecutor

from langchain.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama

# ReAct용 필수 변수 포함 프롬프트
REACT_PROMPT = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "You are a helpful assistant. You have access to the following tools:\n"
        "{tools}\n"
        "Use the following format:\n"
        "Question: {input}\n"
        "Thought: you should always think about what to do\n"
        "Action: the action to take, should be one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the result of the action\n"
        "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer to the original input question\n"
        "\n"
        "Begin!\n"
        "\n"
        "Question: {input}\n"
        "{agent_scratchpad}"
    ),
)

class ReactAgentNode:
    def __init__(self):
        base_url = os.environ.get("OLLAMA_BASE_URL", "")
        llm = ChatOllama(model="llama3", streaming=True, base_url=base_url)
        tools = []  # 사용할 툴이 있다면 여기에 추가
        agent = create_react_agent(llm, tools, prompt=REACT_PROMPT)
        self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    def __call__(self, state):
        # state는 TypedDict로 input 키를 가짐
        input_text = state["input"] if isinstance(state, dict) and "input" in state else state
        return self.executor.invoke({"input": input_text})