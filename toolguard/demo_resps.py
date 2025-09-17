
import asyncio
from datetime import date
from llama_stack.providers.utils.tools.mcp import list_mcp_tools
from llama_stack_client import LlamaStackClient

LLAMA_STACK_URL = "http://localhost:8321/"
MCP_URL = "http://localhost:8765/mcp/"
LLAMA_STACK_MODEL_ID = "openai/gpt-4o"

async def main():
    client = LlamaStackClient(base_url=LLAMA_STACK_URL, max_retries = 0, timeout=600)
    # tools_resp = await list_mcp_tools(MCP_URL, {})
    # print(tools_resp.model_dump_json(indent=2))

    today = date.today()
    instructions = f"today is the {today.day} of {today.strftime('%B %Y')}"
    resp = client.responses.create(
        model=LLAMA_STACK_MODEL_ID,
        # filters=[
        #     "clinic_toolguard"
        # ],
        instructions=instructions,
        input="set an appointement for patient with ssn=12345, with family physician, Dr. David Lee on next Wed, at 10 am. Pay with credit card which ends withh 1234.",
        tools=[
            {
                "type": "mcp",
                "server_url": MCP_URL,
                "server_label": "Clinic tools",
            } # type: ignore
        ],
        # stream=True
    )
        # for event in stream:
        #     print(event.type)
        # final_response = stream.get_final_response()
        # print(final_response.model_dump_json(indent=2))
    print(resp.model_dump_json(indent=2))

asyncio.run(main())
