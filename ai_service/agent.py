from time import time
from dotenv import load_dotenv
from fastapi import HTTPException
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.globals import set_llm_cache, set_verbose
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import Tool

from llm.model import ChatModel
from ai_service.prompts import AgentPromptTemplate
from utils.logging_util import get_logger
from utils.response_codes import ResponseCodes
from ai_service.session_manager import SessionManager
from ai_service.hybrid_session_manager import get_hybrid_session_manager
from RAG.vectorizer import search_weaviate


load_dotenv()
logger = get_logger(__name__)

# Set the LLM cache
set_llm_cache(False)
set_verbose(True)


def weaviate_retriever_function(query: str, tenant_id: str = None, file_id: str = None) -> str:
    """
    Retrieve relevant legal text from Weaviate vector store.
    
    Args:
        query: The search query
        tenant_id: Optional tenant ID to filter results
        file_id: Optional file ID to filter results
    
    Returns:
        Formatted string of relevant document chunks
    """
    try:
        results = search_weaviate(query, k=3, tenant_id=tenant_id, file_id=file_id)
        if not results:
            return "No relevant information found in the uploaded documents."
        
        # Format results as a string
        formatted_chunks = []
        for result in results:
            content = result.get("content", "").strip()
            filename = result.get("filename", "unknown")
            formatted_chunks.append(f"[From: {filename}]\n{content}")
        
        return "\n\n---\n\n".join(formatted_chunks)
    except Exception as e:
        logger.error(f"Error retrieving from Weaviate: {e}", exc_info=True)
        return f"Error retrieving documents: {str(e)}"


class ChatAgent:
    def __init__(self, payload) -> None:
        assert isinstance(payload, dict), "Payload must be a dictionary"
        logger.info(f"AI Agent received Payload: {payload}")

        self.payload = payload
        self.tenant_id = str(payload.get("tenant_id", ""))
        self.query = payload.get("message", "")
        self.memory = None

        # Initialize your custom prompt builder
        self.agent_prompt = AgentPromptTemplate(tenant_id=self.tenant_id)

    async def ai_agent(self):
        try:
            start_time = time()

            # Persistent memory using hybrid session manager (Redis + PostgreSQL)
            hybrid_manager = await get_hybrid_session_manager()
            self.memory = await hybrid_manager.get_memory(self.tenant_id)

            # Create Weaviate retriever tool with tenant filtering
            def retriever_with_tenant(query: str) -> str:
                return weaviate_retriever_function(query, tenant_id=self.tenant_id)
            
            retriever_tool = Tool(
                name="legal_retriever",
                description="Retrieve relevant legal text from uploaded documents in the Weaviate vector database. Use this tool to search for information in uploaded legal PDFs.",
                func=retriever_with_tenant,
            )
            self.tools = [retriever_tool]

            # Build your custom system/user prompt
            self.prompt = await self.agent_prompt.create_agent_prompt()

            # Chain setup
            runnable_chain = RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"])
            )

            # If we have tools, bind them to model functions
            if self.tools:
                chat_model = ChatModel.chat_model.bind_functions(functions=self.tools)
            else:
                chat_model = ChatModel.chat_model

            base_chain = (
                self.prompt
                | chat_model
                | OpenAIFunctionsAgentOutputParser()
            )

            agent_chain = runnable_chain | base_chain

            agent_executor = AgentExecutor(
                agent=agent_chain,
                tools=self.tools,
                verbose=True,
                memory=self.memory,
                return_intermediate_steps=True,
            )

            # Execute the reasoning chain
            response = await agent_executor.ainvoke(
                input={"query": self.query},
                config={"configurable": {"session_id": self.tenant_id}},
            )

            output = response.get("output", "").strip()
            
            # Save conversation turn to both Redis and PostgreSQL
            hybrid_manager = await get_hybrid_session_manager()
            await hybrid_manager.save_conversation_turn(
                tenant_id=self.tenant_id,
                user_message=self.query,
                assistant_message=output
            )

            # Return structured result
            return {
                "status": ResponseCodes.SUCCESS,
                "tenantId": self.tenant_id,
                "response": output,
                "time": round((time() - start_time), 2),
            }

        except Exception as e:
            logger.error(f"AI Agent error: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))


# Memory chat using retrieval without tools
# class ChatAgent:
#     def __init__(self, payload) -> None:
#         assert isinstance(payload, dict), "Payload must be a dictionary"
#         logger.info(f"AI Agent received Payload: {payload}")

#         self.payload = payload
#         self.tenant_id = str(payload.get("tenant_id", ""))
#         self.query = payload.get("message", "")
#         self.filename = payload.get("filename", "uploaded_legal_doc")

#         self.agent_prompt = AgentPromptTemplate(tenant_id=self.tenant_id)
#         self.memory = None  # will be set dynamically per session

#     async def ai_agent(self):
#         """
#         Executes a conversational RAG reasoning chain using persistent memory.
#         """
#         try:
#             start_time = time()
#             self.memory = await SessionManager.get_memory(self.tenant_id)

#             # Retrieve RAG context
#             context = IndexRetriever.legal_knowledge_base(self.query)

#             # Prepare prompt with conversation memory
#             past_messages = self.memory.load_memory_variables({}).get("chat_history", [])
#             formatted_memory = "\n".join([f"User: {m.content}" if m.type == "human" else f"Agent: {m.content}" for m in past_messages])

#             prompt = f"""
# You are Grant AI, a legal assistant.
# Maintain continuity with previous exchanges and answer clearly.

# Past conversation:
# {formatted_memory}

# Context:
# {context}

# User's new question:
# {self.query}
# """

#             # Generate model response
#             response = await ChatModel.chat_model.ainvoke(prompt)
#             agent_output = response.content.strip()

#             # Update memory
#             self.memory.chat_memory.add_user_message(self.query)
#             self.memory.chat_memory.add_ai_message(agent_output)

#             # Return structured result
#             return {
#                 "status": ResponseCodes.SUCCESS,
#                 "tenantId": self.tenant_id,
#                 "response": agent_output,
#                 "time": round((time() - start_time), 2),
#             }

#         except Exception as e:
#             logger.error(f"AI Agent error: {e}", exc_info=True)
#             raise HTTPException(status_code=502, detail=str(e))