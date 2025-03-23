import anthropic
from tools import *

client = anthropic.Anthropic()
system_prompt = """
You are an intelligent research assistant.
You are given a research topic and must generate a list of Wikipedia articles that are relevant to the research topic.
You have access to a set of tools but only use the ones that are relevant for the task at hand.
"""

def get_research_help(topic: str, num_articles: int):
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Generate {num_articles} articles for the research topic {topic}"
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
            system=system_prompt,
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

get_research_help("Pirates Across the World", 7)