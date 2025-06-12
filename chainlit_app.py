import chainlit as cl
import os
from dotenv import load_dotenv
import time
from llama_stack_client import LlamaStackClient
from llama_stack_client.types import UserMessage

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
MODEL_ID = os.getenv("INFERENCE_MODEL", "llama3.2:1b")

# Global client
client = None


async def get_llm_response(message: str) -> str:
    """Get response from Llama Stack"""
    if not client:
        return "System not initialized. Please refresh and try again."
    
    start_time = time.time()
    
    try:
        response = client.inference.chat_completion(
            model_id=MODEL_ID,
            messages=[UserMessage(role="user", content=message)],
            stream=False
        )
        
        result = response.completion_message.content if response and response.completion_message else "No response generated."
        elapsed = time.time() - start_time
        return f"{result}\n\n⏱️ *Response time: {elapsed:.1f} seconds*"
        
    except Exception as e:
        return f"Error: {str(e)}"

# ====== CHAINLIT HANDLERS ======

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    global client
    
    try:
        client = LlamaStackClient(base_url=API_URL)
        await cl.Message(content="Hello! I'm powered by Llama Stack. How can I help you today?").send()
    except Exception as e:
        await cl.Message(content=f"Failed to connect to Llama Stack: {str(e)}").send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages"""
    response = await get_llm_response(message.content)
    await cl.Message(content=response).send()

