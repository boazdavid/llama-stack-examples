import os
from llama_stack_client import LlamaStackClient

# Initialize the client
llama_stack_url = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
client = LlamaStackClient(base_url=llama_stack_url)

# List available models
print("Available models:")
models = client.models.list()
for model in models:
    print(f"  - {model.identifier} ({model.model_type})")

# Select the LLM model
model_id = os.getenv("INFERENCE_MODEL", "llama3.2:1b")
print(f"\nUsing model: {model_id}")

# Simple chat completion
print("\nTesting inference...")
response = client.inference.chat_completion(
    model_id=model_id,
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ],
    stream=False
)

print(f"Response: {response.completion_message.content}")