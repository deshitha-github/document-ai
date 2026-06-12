import os
from dotenv import find_dotenv
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts import SystemMessagePromptTemplate

load_dotenv(find_dotenv())

CHATBOT_NAME = os.getenv("CHATBOT_NAME")

class AgentPromptTemplate:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    async def create_agent_prompt(self):
        """
        Create an agent prompt template for the chatbot.
        """

        system_message = f"""
Your name is {CHATBOT_NAME}. \
You are an AI legal assistant. You must *always* use the `legal_retriever` tool 
to answer user questions, regardless of whether you know the answer. 
Do not rely on your own knowledge; instead, retrieve text from the knowledge base 
and summarize it for the user. If retrieval returns no relevant result, reply:
"I couldn’t find relevant information about that in the uploaded documents."
"""
        return ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(
                    template=system_message,
                ),
                MessagesPlaceholder(
                    variable_name="chat_history",
                    optional=True,
                ),
                HumanMessagePromptTemplate.from_template("{query}"),
                MessagesPlaceholder(variable_name="agent_scratchpad", optional=True),
            ],
        )
