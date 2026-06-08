from langchain.agents import create_agent
from tools.file_tools import run_terminal
from dotenv import load_dotenv

load_dotenv()

chat_agent = create_agent(
    model="google_genai:gemini-3.1-flash-lite",
    tools=[run_terminal],
    system_prompt="""You are an agent who asks questions to the user to know what problem they want to solve in their project and what bugs need to be found.
            Keep your answers short and straight to the point, dont ask for github or any files from the user, there is a option given to the user , to enter 
            "done" or "scan" then the user can enter path of the project and you can work on it. Keep it short , help user explaining what to do, keep your answers 1-2 lines.
            and if user have said his thoughts then ask them to enter "done" or "scan"
    """
)