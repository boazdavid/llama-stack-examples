# Responses API Examples

This directory contains examples demonstrating how to use the Llama Stack Responses API for various AI applications including simple inference, Retrieval-Augmented Generation (RAG), and Model Context Protocol (MCP) tool calling.

## Overview

The Responses API provides a unified interface for AI interactions that can handle:

- Simple model inference
- Retrieval-Augmented Generation with document search
- Tool calling through Model Context Protocol (MCP) servers
- Complex multi-step workflows

## Files in this Directory

- [responses-api.ipynb](./responses-api.ipynb) - Main Python notebook with comprehensive examples
- [nps_mcp_server.py](./nps_mcp_server.py) - US National Park Service MCP server implementation
- [requirements.txt](./requirements.txt) - Python dependencies for running the examples
- [run.yaml](./run.yaml) - Llama Stack configuration file
- [README.md](./README.md) - This file.
- [README_NPS.md](./README_NPS.md) - Additional README file with more information about the National Park Service MCP server.

## Instructions

To see all the prerequisites for running the notebook and how to meet them, see the instructions at the start of the notebook.

## What You'll Learn

The notebook demonstrates three main approaches to using the Responses API:

### 1. Llama Stack Client

- Direct integration with Llama Stack
- Complete control over API interactions
- Best for users new to the ecosystem

### 2. OpenAI Client

- Using OpenAI's client library with Llama Stack
- Good for existing projects already using the OpenAI client
- Requires URL suffix: `/v1/openai/v1`

### 3. LangChain Integration

- Higher-level abstractions for complex workflows
- Framework-based approach
- Simplified code with `use_responses_api=True`

## Troubleshooting

### Common Issues

1. **Port already in use**: If port 8321 or 3005 is busy, use different ports:
   ```bash
   llama stack run run.yaml --image-type venv --port 8322
   python nps_mcp_server.py --transport sse --port 3006
   ```

2. **API key not working**: Verify your API keys are correctly set:
   ```bash
   echo $OPENAI_API_KEY  # Should show your key
   ```

3. **Python version issues**: Ensure you're using Python 3.12+:
   ```bash
   python --version
   ```

4. **Dependency conflicts**: Use a fresh virtual environment if you encounter package conflicts.

## Support

This notebook and README were developed with assistance from Google Gemini and Cursor using Claude Sonnet 4. For issues with:

- **Llama Stack**: Check the [official documentation](https://llama-stack.readthedocs.io/)
- **MCP Protocol**: See [Model Context Protocol docs](https://modelcontextprotocol.io/)
- **This example**: Review the notebook cells for detailed explanations
