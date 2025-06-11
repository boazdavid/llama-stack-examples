# For dev testing only

import os
from dotenv import load_dotenv
from llama_stack_client import LlamaStackClient
from llama_stack_client.types import UserMessage

def main():
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    endpoint = os.getenv("LLAMA_STACK_API_URL", "http://localhost:5000")
    model_id = os.getenv("INFERENCE_MODEL", "llama3.2:1b")
    
    # Initialize client
    client = LlamaStackClient(base_url=endpoint)
    
    # Test chat completion
    print(f"Testing chat completion with model: {model_id}")
    print(f"Endpoint: {endpoint}")
    print("-" * 50)
    
    try:
        response = client.inference.chat_completion(
            model_id=model_id,
            messages=[
                UserMessage(
                    role="user",
                    content="write a haiku for meta's llama models"
                )
            ],
            stream=False
        )
        
        print("Response:")
        print(response.completion_message.content)
        
        if response.metrics:
            print("\nMetrics:")
            for metric in response.metrics:
                print(f"  {metric.metric}: {metric.value}")
                
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
