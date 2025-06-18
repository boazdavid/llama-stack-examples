import chainlit as cl
import os
import asyncio
from dotenv import load_dotenv
from llama_stack_client import Agent, AgentEventLogger, RAGDocument, LlamaStackClient

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "my_demo_vector_db")

# Global variables
client = None
agent = None
session_id = None
initialization_complete = False
llm_model_id = None


async def initialize():
    """Initialize system with console output only"""
    global client, agent, initialization_complete, llm_model_id
    
    if initialization_complete:
        return
    
    try:
        # Initialize client
        print(f"🔌 Connecting to Llama Stack API at {API_URL}...")
        client = LlamaStackClient(base_url=API_URL, timeout=120)
        print("✅ Connected to API")
        
        # Get models
        print("🔍 Loading models...")
        models = client.models.list()
        llm_model = next(m for m in models if m.model_type == "llm")
        embedding_model = next(m for m in models if m.model_type == "embedding")
        llm_model_id = llm_model.identifier
        print(f"🚀 Using LLM: {llm_model_id}")
        print(f"🧠 Using embedding: {embedding_model.identifier}")
        
        # Setup vector DB
        print(f"📊 Setting up vector database: {VECTOR_DB_ID}...")
        try:
            client.vector_dbs.register(
                vector_db_id=VECTOR_DB_ID,
                embedding_model=embedding_model.identifier,
                embedding_dimension=embedding_model.metadata["embedding_dimension"],
                provider_id="faiss",
            )
            print("✅ Vector database ready")
        except:
            print("⚠️ Vector database already registered")
        
        # Load document  
        print("📄 Loading document...")
        source_url = "https://www.paulgraham.com/greatwork.html"
        document = RAGDocument(
            document_id="document_1",
            content=source_url,
            mime_type="text/html",
            metadata={},
        )
        
        try:
            client.tool_runtime.rag_tool.insert(
                documents=[document],
                vector_db_id=VECTOR_DB_ID,
                chunk_size_in_tokens=50,  # Smaller chunks like demo_script
            )
            print("✅ Document loaded and indexed")
        except Exception as e:
            print(f"⚠️ Document load failed: {str(e)}")
            print("⚠️ Continuing without document - basic chat still available")
        
        # Create agent
        print("🤖 Creating AI agent...")
        agent = Agent(
            client,
            model=llm_model_id,
            instructions="You are a helpful assistant with access to knowledge search tools. When answering questions, first search for relevant information using your available tools before providing a response.",
            tools=[{
                "name": "builtin::rag/knowledge_search",
                "args": {"vector_db_ids": [VECTOR_DB_ID]},
            }],
        )
        
        initialization_complete = True
        print("✅ System initialized successfully")
        
    except Exception as e:
        print(f"❌ Initialization error: {str(e)}")
        raise e


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    global session_id
    print("=== Starting new chat session ===")
    print("📱 UI: Displaying welcome message...")
    
    # Show welcome message first
    await cl.Message("👋 **Welcome to Llama Stack Chat!**\n\n🔄 Initializing system...").send()
    print("✅ UI: Welcome message sent")
    
    # Do initialization in background (console only, no UI updates)
    try:
        print("🔄 UI: Starting initialization...")
        await initialize()
        
        # Create session after successful initialization
        print("📝 UI: Creating agent session...")
        session_id = agent.create_session("chat_session")
        print(f"📝 Created session: {session_id}")
        
        # Show ready message
        print("📱 UI: Preparing ready message...")
        if agent:
            ready_msg = f"✅ **System Ready!**\n\n🤖 Using: {llm_model_id}\n📄 Document: Paul Graham essay\n\n💬 Ask me anything!"
            await cl.Message(ready_msg).send()
            print("✅ UI: Ready message sent")
        else:
            await cl.Message("⚠️ **Partial initialization** - some features may be limited.").send()
            print("⚠️ UI: Partial initialization message sent")
        
    except Exception as e:
        error_msg = f"❌ **Initialization failed:** {str(e)}\n\n🔄 The system may still be starting up. Please wait a moment and refresh."
        print(f"❌ Initialization error: {str(e)}")
        print("📱 UI: Sending error message...")
        await cl.Message(error_msg).send()
        print("❌ UI: Error message sent")


@cl.set_starters
async def set_starters():
    """Set starter suggestions for the user"""
    print("📱 UI: Setting up starter suggestions...")
    starters = [
        cl.Starter(
            label="What are the key ideas?",
            message="What are the key ideas about doing great work according to Paul Graham?",
        ),
        cl.Starter(
            label="How to find what to work on?",
            message="According to Paul Graham, how do you find what to work on?",
        ),
        cl.Starter(
            label="Role of curiosity?",
            message="What does Paul Graham say about the role of curiosity in doing great work?",
        ),
        cl.Starter(
            label="Dealing with setbacks?",
            message="What advice does Paul Graham give about dealing with setbacks and failures?",
        ),
    ]
    print(f"✅ UI: {len(starters)} starter suggestions configured")
    return starters


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages"""
    global session_id
    print(f"\n📥 UI: Received user message: {message.content}")
    print(f"🔍 UI: Checking system readiness (agent: {agent is not None}, session: {session_id is not None})")
    
    if not agent or not session_id:
        error_msg = "\u26a0\ufe0f System not ready. Please refresh the page."
        print(f"❌ UI: System not ready - {error_msg}")
        print("📤 UI: Sending error response...")
        await cl.Message(error_msg).send()
        print("✅ UI: Error response sent")
        return
    
    try:
        print("🤖 Creating agent response...")
        # Get response from agent
        response = agent.create_turn(
            messages=[{"role": "user", "content": message.content}],
            session_id=session_id,
            stream=True
        )
        
        # Process response using AgentEventLogger like demo_script
        response_text = ""
        for log in AgentEventLogger().log(response):
            # Look for inference logs which contain the actual response content
            if hasattr(log, 'role') and log.role == 'inference' and hasattr(log, 'content') and log.content and str(log.content).strip():
                # Skip tool calls and JSON - only collect actual text content
                content = str(log.content)
                if not content.startswith('[') and not content.startswith('{') and '"name"' not in content:
                    response_text += content
        
        final_response = response_text.strip() or "No response generated."
        print(f"🤖 Assistant: {final_response[:100]}..." if len(final_response) > 100 else f"🤖 Assistant: {final_response}")
        print("📤 Sending response to UI...")
        await cl.Message(final_response).send()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        await cl.Message(f"Error: {str(e)}").send()