import chainlit as cl
import os
from dotenv import load_dotenv
import time
import logging
from llama_stack_client import Agent, AgentEventLogger, RAGDocument, LlamaStackClient
from llama_stack_client.types import UserMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "my_demo_vector_db")

# Global variables
client = None
agent = None
model_id = None
embedding_model_id = None
embedding_dimension = None
session_id = None


async def get_agent_response(message: str) -> str:
    """Get response from Llama Stack Agent with RAG capabilities"""
    if not agent:
        logger.error("Agent not initialized")
        return "System not initialized. Please refresh and try again."
    
    start_time = time.time()
    logger.info(f"Getting agent response for: {message[:50]}...")
    
    try:
        logger.info(f"Creating turn with session_id: {session_id}")
        response = agent.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=session_id,
            stream=True
        )
        logger.info("Turn created, processing response...")
        
        # Collect response text and tool calls
        response_text = ""
        tool_calls = []
        
        for log in AgentEventLogger().log(response):
            # Check for tool calls
            if hasattr(log, 'tool_call') and log.tool_call:
                tool_name = getattr(log.tool_call, 'tool_name', 'unknown')
                tool_args = getattr(log.tool_call, 'arguments', {})
                tool_calls.append({
                    'name': tool_name,
                    'args': tool_args
                })
            
            # Extract clean response text (skip tool call formatting)
            if hasattr(log, 'text') and log.text:
                # Filter out tool call display text
                if not (log.text.startswith('[') or log.text.startswith('Tool') or 'knowledge_search' in log.text):
                    response_text += log.text
            elif hasattr(log, 'content') and log.content and isinstance(log.content, str):
                # Filter out tool call display text
                if not (log.content.startswith('[') or log.content.startswith('Tool') or 'knowledge_search' in log.content):
                    response_text += log.content
        
        elapsed = time.time() - start_time
        logger.info(f"Response generated in {elapsed:.1f} seconds")
        
        return response_text.strip(), tool_calls, elapsed
        
    except Exception as e:
        logger.error(f"Error getting agent response: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", [], 0

# ====== CHAINLIT HANDLERS ======


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session with RAG capabilities"""
    global client, agent, model_id, embedding_model_id, embedding_dimension, session_id
    
    logger.info("=== Starting chat session ===")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Vector DB ID: {VECTOR_DB_ID}")
    
    try:
        # Initialize client
        logger.info("Initializing LlamaStackClient...")
        client = LlamaStackClient(base_url=API_URL)
        logger.info("Client initialized successfully")
        
        # Get available models
        logger.info("Fetching available models...")
        models = client.models.list()
        logger.info(f"Found {len(models)} models")
        
        # Select the first LLM and embedding models
        logger.info("Selecting models...")
        llm_models = [m for m in models if m.model_type == "llm"]
        embedding_models = [m for m in models if m.model_type == "embedding"]
        
        logger.info(f"Available LLM models: {[m.identifier for m in llm_models]}")
        logger.info(f"Available embedding models: {[m.identifier for m in embedding_models]}")
        
        if not llm_models:
            raise ValueError("No LLM models available")
        if not embedding_models:
            raise ValueError("No embedding models available")
        
        model_id = llm_models[0].identifier
        embedding_model = embedding_models[0]
        embedding_model_id = embedding_model.identifier
        embedding_dimension = embedding_model.metadata.get("embedding_dimension", 768)
        
        logger.info(f"Selected LLM: {model_id}")
        logger.info(f"Selected embedding model: {embedding_model_id} (dim: {embedding_dimension})")
        
        await cl.Message(content=f"🚀 Initializing Llama Stack with:\n- LLM: {model_id}\n- Embedding model: {embedding_model_id}").send()
        
        # Set up vector database
        try:
            logger.info(f"Registering vector database: {VECTOR_DB_ID}")
            _ = client.vector_dbs.register(
                vector_db_id=VECTOR_DB_ID,
                embedding_model=embedding_model_id,
                embedding_dimension=embedding_dimension,
                provider_id="faiss",
            )
            logger.info("Vector database registered successfully")
        except Exception as e:
            # Vector DB might already be registered
            logger.warning(f"Vector DB registration failed (might already exist): {str(e)}")
        
        # Hardcode document ingestion like demo_script.py
        logger.info("Ingesting Paul Graham document...")
        source = "https://www.paulgraham.com/greatwork.html"
        document = RAGDocument(
            document_id="document_1",
            content=source,
            mime_type="text/html",
            metadata={},
        )
        
        try:
            client.tool_runtime.rag_tool.insert(
                documents=[document],
                vector_db_id=VECTOR_DB_ID,
                chunk_size_in_tokens=50,
            )
            logger.info(f"Document ingested successfully: {source}")
            await cl.Message(content=f"📄 Document ingested: Paul Graham's 'How to do great work'\n\nReady to answer questions!").send()
        except Exception as e:
            logger.error(f"Failed to ingest document: {str(e)}")
            await cl.Message(content=f"⚠️ Failed to ingest document, but you can still chat: {str(e)}").send()
        
        # Create agent with RAG tool
        logger.info("Creating agent...")
        agent = Agent(
            client,
            model=model_id,
            instructions="You are a helpful assistant",
            tools=[
                {
                    "name": "builtin::rag/knowledge_search",
                    "args": {"vector_db_ids": [VECTOR_DB_ID]},
                }
            ],
        )
        logger.info("Agent created successfully")
        
        # Create session
        logger.info("Creating session...")
        session_id = agent.create_session("chainlit_rag_session")
        logger.info(f"Session created: {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {str(e)}", exc_info=True)
        await cl.Message(content=f"Failed to initialize: {str(e)}").send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages"""
    logger.info(f"Received message: {message.content[:50]}...")
    result = await get_agent_response(message.content)
    
    if isinstance(result, tuple):
        response_text, tool_calls, elapsed = result
        
        # Show tool calls as action steps
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                await cl.Message(content=f"🔧 **Tool Call:** {tool_name}\n```json\n{tool_args}\n```").send()
        
        # Send final response
        final_response = f"{response_text}\n\n⏱️ *Response time: {elapsed:.1f} seconds*"
        logger.info(f"Sending response: {final_response[:50]}...")
        await cl.Message(content=final_response).send()
    else:
        # Handle error case
        logger.info(f"Sending response: {result[:50]}...")
        await cl.Message(content=result).send()


