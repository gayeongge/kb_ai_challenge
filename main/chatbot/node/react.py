import os

from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_ollama import ChatOllama

from win32comext.adsi.demos.scp import verbose

from state.schema import OutputState

from dotenv import load_dotenv
load_dotenv()

# ReAct용 필수 변수 포함 프롬프트
REACT_PROMPT = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template=(
        "You must always use the following format and never reply in any other way."
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
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "")
        llm = ChatOllama(model="gemma3:1b", streaming=True, base_url=self.base_url)
        add_tool = Tool(
            name="Calculator",
            func=self.add_numbers,
            description="Adds numbers given as space-separated input. Example input: '3 5'"
        )
        tools = [add_tool]  # 사용할 툴이 있다면 여기에 추가
        # agent = create_react_agent(llm, tools, state_modifier=REACT_PROMPT)
        agent = initialize_agent(
            tools,
            llm,
            agent= AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        # self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        self.executor = agent

    @staticmethod
    def add_numbers(input:str)-> str:
        try:
            return str("10")
        except Exception:
            return "Error..."


    def __call__(self, state)-> OutputState:
        # state는 TypedDict로 input 키를 가짐
        input_text = state["input"] if isinstance(state, dict) and "input" in state else state
        output = self.executor.invoke({"input": input_text})['output']
        return OutputState(output=output)
