# llama stack demo app

Demo app with llama stack quickstart and additional UI built with chainlit.


## Getting Started
### Quick Start
- Install docker

- Copy the environment file (and customize if needed):
   ```bash
   cp .env.example .env
   ```

- Start all services:
   ```bash
   docker compose up -d
   ```

- Wait for all services to be healthy and then access the applications in your browser - these are the default ports if you did not customize them in the `.env` file:
   - **Chainlit Chat Interface**: http://localhost:9090
   - **Llama Stack Playground**: http://localhost:8501


### Development Setup
- Install uv and run uv sync to install python dependencies

- Run llama-stack via client CLI with chat completion:
   ```bash
   uv run llama-stack-client --endpoint http://localhost:5001 \
   inference chat-completion \
   --model-id llama3.2:1b \
   --message "write a haiku for meta's llama models"
   ```

- Run the demo client: `uv run demo_01_client.py`


## Features

- **RAG (Retrieval Augmented Generation)**: The Chainlit app includes document ingestion and RAG capabilities
- **Multiple UIs**: Choose between the official Llama Stack Playground or the custom Chainlit interface
- **Dockerized Setup**: All services run in containers with proper health checks and dependencies
- **Auto Model Pulling**: Ollama automatically pulls the specified model on startup

## Notes

- Tool calling with small models is inconsistent - sometimes it works sometimes it doesn't - need to use a bigger model for more consistent results
- The Chainlit app automatically ingests documents on startup, which may take some time
- All services use environment variables for configuration - customize via `.env` file

## Architecture

The project consists of four main services:
1. **Ollama**: Provides local LLM inference
2. **Llama Stack**: API server that interfaces with Ollama
3. **Llama Stack Playground**: Official web UI for testing
4. **Chainlit App**: Custom chat interface with RAG capabilities

All services are orchestrated via Docker Compose with proper health checks and startup dependencies.


# TODO
- [ ] Improve demo UI 
   - Add RAG steps (like Allycat)
   - Add AI Alliance branding (like Allycat)
   - Explore other UI frameworks (e.g. open-webui)
- [ ] Merge llama-stack-playground with llama-stack container
- [ ] Document llamastack issues
    - undeclared dependencies for client: fire, requests
    - ollama distribution embedding model name mismatch: `all-MiniLM-L6-v2` vs `all-minilm:latest`