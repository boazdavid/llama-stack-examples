
import asyncio
from llama_stack.providers.utils.tools.mcp import list_mcp_tools
from llama_stack_client import LlamaStackClient

LLAMA_STACK_URL = "http://localhost:8321/"
MCP_URL = "http://localhost:8765/mcp/"
LLAMA_STACK_MODEL_ID = "openai/gpt-4o"

client = LlamaStackClient(base_url=LLAMA_STACK_URL)
async def main():
    tools_resp = await list_mcp_tools(MCP_URL, {})
    print(tools_resp.model_dump_json(indent=2))

    response = client.responses.create(
        model=LLAMA_STACK_MODEL_ID,
        # filters=[
        #     "clinic_toolguard"
        # ],
        input="set an appointement for patient with ssn=12345, with my family physician, Dr. David Lee on 17 of September 2025, at 10 am.",
        tools=[
            {
                "type": "mcp",
                "server_url": MCP_URL,
                "server_label": "Clinic tools",
            }
            # {
            #     "type": "function",
            #     "name": "list_all_airports",
            #     "description": "Returns a list of all available airports.",
            #     "parameters": {}
            # }
            # book_resrervation_tool,
            # list_airports_tool
        ]
    )
    print(response.model_dump_json(indent=2))

asyncio.run(main())
