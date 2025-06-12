import os
from dotenv import load_dotenv
from llama_stack_client import Agent, AgentEventLogger, RAGDocument, LlamaStackClient

load_dotenv()

vector_db_id = os.getenv("VECTOR_DB_ID", "my_demo_vector_db")
llama_stack_url = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
client = LlamaStackClient(base_url=llama_stack_url)

models = client.models.list()

# Select the first LLM and first embedding models
model_id = next(m for m in models if m.model_type == "llm").identifier
embedding_model_id = (
    em := next(m for m in models if m.model_type == "embedding")
).identifier
embedding_dimension = em.metadata["embedding_dimension"]

_ = client.vector_dbs.register(
    vector_db_id=vector_db_id,
    embedding_model=embedding_model_id,
    embedding_dimension=embedding_dimension,
    provider_id="faiss",
)
source = "https://www.paulgraham.com/greatwork.html"
print("rag_tool> Ingesting document:", source)
document = RAGDocument(
    document_id="document_1",
    content=source,
    mime_type="text/html",
    metadata={},
)
client.tool_runtime.rag_tool.insert(
    documents=[document],
    vector_db_id=vector_db_id,
    chunk_size_in_tokens=50,
)
agent = Agent(
    client,
    model=model_id,
    instructions="You are a helpful assistant with access to knowledge search tools. When answering questions, first search for relevant information using your available tools before providing a response.",
    tools=[
        {
            "name": "builtin::rag/knowledge_search",
            "args": {"vector_db_ids": [vector_db_id]},
        }
    ],
)

prompt = "How do you do great work?"
print("prompt>", prompt)

response = agent.create_turn(
    messages=[{"role": "user", "content": prompt}],
    session_id=agent.create_session("rag_session"),
    stream=True,
)

for log in AgentEventLogger().log(response):
    log.print()