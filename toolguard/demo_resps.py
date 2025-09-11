
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

    # from .book_reserv import book_resrervation_tool 
    # from .list_airports import list_airports_tool
    response = client.responses.create(
        model=LLAMA_STACK_MODEL_ID,
        # input="list me all doctors (dont apply any filter) and sort them by name.",
        input="list me all appointements of patient with ssn=12345.",
        # before_tools_shield= ["my_guard"],
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
