# llama stack demo app

This project is a demo app providing a quick-start example using [Llama Stack](https://www.llama.com/products/llama-stack/), and a UI built using [chainlit](https://docs.chainlit.io/get-started/overview).

> [!NOTE]
> This project is a work in progress. It might be a little rough around the edges right now. More detailed getting-started information, as well as debugging tips are coming soon!
>
> **Please join us!** We welcome [PRs](https://github.com/The-AI-Alliance/llama-stack-usecase1/pulls) and suggestions as [issues](https://github.com/The-AI-Alliance/llama-stack-usecase1/issues). Use the [discussions](https://github.com/The-AI-Alliance/llama-stack-usecase1/discussions) for general questions and suggestions. For more information about joining this project or other AI Alliance projects, go [here](https://the-ai-alliance.github.io/contributing/). 

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
