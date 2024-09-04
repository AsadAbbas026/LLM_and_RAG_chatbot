from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.callbacks.base import AsyncCallbackHandler, BaseCallbackHandler
import asyncio
import os
from typing import List, Dict, Any

class MyCustomSyncHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")

class MyCustomAsyncHandler(AsyncCallbackHandler):
    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        print("zzzz....")
        await asyncio.sleep(0.3)
        print("Hi! I just woke up. Your llm is starting")

    async def on_llm_end(self, response: Dict[str, Any], **kwargs) -> None:
        print("zzzz....")
        await asyncio.sleep(0.3)
        print("Hi! I just woke up. Your llm is ending")

class LLMChatbot:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-flash")
        self.session_history = InMemoryChatMessageHistory()

        # Define a chat prompt template
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Write a concise summary of the following:\n\n{context}"),
                ("user", "Question: {question}")
            ]
        )
        self.output_parser = StrOutputParser()

        # Define LLM with history and callbacks
        self.llm_with_history = RunnableWithMessageHistory(
            runnable=self.llm,
            get_session_history=lambda: self.session_history,
            callbacks=[MyCustomSyncHandler(), MyCustomAsyncHandler()],
            input_transform=self.prompt.format,
            output_transform=self.output_parser.parse
        )

    def generate_response(self, user_prompt: str) -> str:
    # Add the new user message to the session history
        self.session_history.add_message({"role": "user", "content": user_prompt})
        # Create a combined input from the context and question
        combined_input = f"{'previous context'} {user_prompt}"
        # Generate response using LLM with history
        llm_response = self.llm_with_history.invoke(combined_input)
        # Extract the content from the AI response
        content = llm_response.content  # Access the content attribute directly
        
        return content


# Instantiate the chatbot and generate a response
#chatbot = LLMChatbot()
#response = chatbot.generate_response("Hello, my name is Asad")
#print(response)
#response = chatbot.generate_response("What is my name?")
#print(response)