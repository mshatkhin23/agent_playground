import anthropic
from .tools import TOOLS

client = anthropic.Anthropic()

def chat_with_claude(query: str):
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": query
                }
            ]
        }
    ]
    while True:
        print(f"Calling Claude with messages: {messages}")
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=1,
            system="You are a world-class stock market analyst. Use the available tools and financial data to answer the user's question.",
            messages=messages,
            tools=TOOLS,
        )
        print(f"Claude response: {response}")
        if response.stop_reason == "tool_use" and response.content:
            tool_message = response.content[-1]
            tool_name = tool_message.name
            tool_input = tool_message.input
            print(f"Calling tool: {tool_name} with input: {tool_input}")
            tool_result = globals()[tool_name](**tool_input)
            print(f"Tool result: {tool_result}")

        elif response.stop_reason == "end_turn":
            print("Claude didn't want to use a tool; ending conversation")
            break
        else:
            break

chat_with_claude("What is the stock price for AAPL?")