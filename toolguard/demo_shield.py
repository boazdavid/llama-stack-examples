
import asyncio
from llama_stack_client import LlamaStackClient

LLAMA_STACK_URL = "http://localhost:8321/"

client = LlamaStackClient(base_url=LLAMA_STACK_URL)
async def main():
    shields = client.shields.list()
    for shield in shields:
        print(shield.identifier)

    shield = client.shields.register(
        shield_id="clinic_toolguard",
        params={
            "path": "../gen_policy_validator/eval/clinic/output/step2_claude4sonnet",
            "touch_points":["tool_input"]
        },
        provider_id="tool-guard",
    )

    resp = client.safety.run_shield(messages=[], shield_id="clinic_toolguard", params={})
    print(resp)

    shields = client.shields.list()
    for shield in shields:
        print(shield.identifier)

asyncio.run(main())
