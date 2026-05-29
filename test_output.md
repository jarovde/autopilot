# How to Build a Production-Ready Claude Chatbot in Python

Building a simple script that calls an LLM is easy. But building a **production-ready** chatbot requires handling real-world challenges: managing conversation state, streaming responses in real-time to keep users engaged, and gracefully handling API errors.

In this guide, we will build a robust, stateful CLI chatbot using Python and Anthropic's latest SDK, powered by **Claude 3.5 Sonnet**. 

By the end of this article, you will have a clean, object-oriented chatbot engine that you can drop straight into a FastAPI backend or a desktop app.

---

### Prerequisites

First, make sure you have Python 3.8+ installed. You'll need to install the official Anthropic SDK and `python-dotenv` to manage your API keys securely.

```bash
pip install anthropic python-dotenv
```

Next, grab your API key from the [Anthropic Console](https://console.anthropic.com/) and add it to a `.env` file in your project root:

```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

---

### Step 1: Design the Chatbot Engine

To make our chatbot production-ready, we need to encapsulate state management (the conversation history) and streaming logic inside a reusable class. 

Here is the implementation of our `ClaudeChatbot` engine. Save this file as `chatbot.py`:

```python
import os
from typing import Generator, List, Dict
from anthropic import Anthropic, APIError

class ClaudeChatbot:
    def __init__(self, api_key: str = None, system_prompt: str = None):
        # Fallback to environment variable if api_key is not passed explicitly
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-latest"
        self.system_prompt = system_prompt or "You are a helpful, concise assistant."
        self.history: List[Dict[str, str]] = []

    def _add_message(self, role: str, content: str) -> None:
        """Appends a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def stream_response(self, user_message: str) -> Generator[str, None, None]:
        """
        Sends a message to Claude and yields the response chunks in real-time.
        Automatically updates conversation history upon success.
        """
        self._add_message("user", user_message)
        
        try:
            # Use the streaming API for real-time response delivery
            with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=self.history
            ) as stream:
                assistant_response = ""
                for text in stream.text_stream:
                    assistant_response += text
                    yield text
                
                # Append Claude's complete response to history for context retention
                self._add_message("assistant", assistant_response)
                
        except APIError as e:
            # Cleanly catch and yield API errors (rate limits, invalid keys, etc.)
            error_msg = f"\n[API Error: {e.message}]"
            yield error_msg
        except Exception as e:
            # Fallback for unexpected connection issues
            error_msg = f"\n[Unexpected Error: {str(e)}]"
            yield error_msg
```

#### Why this is production-grade:
1. **Streaming Support:** Using `client.messages.stream()` allows you to deliver responses token-by-token. This dramatically improves the perceived latency for your users.
2. **Robust Error Handling:** It wraps API calls in `try-except` blocks to catch `APIError` from the Anthropic SDK. If the network drops or you hit a rate limit, the application won't crash.
3. **Encapsulated State:** Conversation history is maintained internally.

---

### Step 2: Create the Interactive CLI Loop

Now, let's build the entry point that initializes our chatbot, loads environment variables, and manages the interactive CLI loop. Save this as `app.py`:

```python
import os
from dotenv import load_dotenv
from chatbot import ClaudeChatbot

# Load API key from .env
load_dotenv()

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is missing.")
        print("Please set it in your .env file.")
        return

    # Define a system prompt to give your bot a specific persona
    system_instruction = (
        "You are a senior Python developer. Give precise, "
        "well-commented code examples and explain concepts briefly."
    )

    # Initialize the chatbot
    bot = ClaudeChatbot(api_key=api_key, system_prompt=system_instruction)

    print("==================================================")
    print("  Claude 3.5 Sonnet Chatbot (Type 'exit' to quit) ")
    print("==================================================")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            # Print Claude's response in real-time as it streams in
            print("Claude: ", end="", flush=True)
            for chunk in bot.stream_response(user_input):
                print(chunk, end="", flush=True)
            print()  # Add a newline at the end of the stream

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nSession interrupted. Goodbye!")
            break

if __name__ == "__main__":
    main()
```

Run your application using:
```bash
python app.py
```

---

### Scaling to Production: Next Steps

While this CLI tool works perfectly for testing, taking this to a web-scale production environment requires a few shifts:

1. **Persistent Memory:** Instead of an in-memory `self.history` list, store user conversations in a database like PostgreSQL or Redis. Retrieve the last $N$ messages when a user opens a chat session.
2. **Web Frameworks:** Wrap the `stream_response` generator in a FastAPI `StreamingResponse` using Server-Sent Events (SSE). This allows your frontend React/Vue app to consume the stream natively.
3. **Context Window Management:** If conversations get extremely long, your history will consume too many tokens. Implement a sliding window or summary strategy to prune older messages.

### Wrap Up

You now have a clean, modular Python chatbot class that handles state, streams responses, and handles errors gracefully. You can easily adapt this to run inside serverless functions, Discord bots, or web APIs.

*Are you planning to build with Claude 3.5 Sonnet? Let me know in the comments what kind of AI application you are building next!*