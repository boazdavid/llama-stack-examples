
import asyncio
from llama_stack_client import LlamaStackClient

LLAMA_STACK_URL = "http://localhost:8321/"

client = LlamaStackClient(base_url=LLAMA_STACK_URL)
async def main():
    shields = client.shields.list()
    for shield in shields:
        print(shield.identifier)

    shield = client.shields.register(
        shield_id="airline_toolguard",
        params={
            "path": "123"
        },
        provider_id="tool-guard",
    )

    resp = client.safety.run_shield(messages=[], shield_id="airline_toolguard", params={})
    print(resp)

    shields = client.shields.list()
    for shield in shields:
        print(shield.identifier)

asyncio.run(main())
