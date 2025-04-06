from fake_db import FakeDatabase
import typer
    
import anthropic
import json

tool_get_order_by_id = {
    "name": "get_order_by_id",
    "description": "Retrieves the details of a specific order based on the order ID. Returns the order ID, product name, quantity, price, and order status.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique identifier for the order."
            }
        },
        "required": ["order_id"]
    }
}

tool_get_user = {
    "name": "get_user",
    "description": "Looks up a user by email, phone, or username.",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "enum": ["email", "phone", "username"],
                "description": "The attribute to search for a user by (email, phone, or username)."
            },
            "value": {
                "type": "string",
                "description": "The value to match for the specified attribute."
            }
        },
        "required": ["key", "value"]
    }
}

tool_get_customer_orders = {
    "name": "get_customer_orders",
    "description": "Retrieves the list of orders belonging to a user based on a user's customer id.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "The customer_id belonging to the user"
            }
        },
        "required": ["customer_id"]
    }
}

tool_cancel_order = {
    "name": "cancel_order",
    "description": "Cancels an order based on a provided order_id.  Only orders that are 'processing' can be cancelled",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order_id pertaining to a particular order"
            }
        },
        "required": ["order_id"]
    }
}

tools = [tool_get_order_by_id, tool_get_user, tool_get_customer_orders, tool_cancel_order]
client = anthropic.Client()
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"
app = typer.Typer()
db = FakeDatabase()

def process_tool_call(tool_use):
    tool_name = tool_use.name
    tool_input = tool_use.input
    if tool_name == "get_user":
        content = db.get_user(tool_input["key"], tool_input["value"])
    elif tool_name == "get_order_by_id":
        content = db.get_order_by_id(tool_input["order_id"])
    elif tool_name == "get_customer_orders":
        content = db.get_customer_orders(tool_input["customer_id"])
    elif tool_name == "cancel_order":
        content = db.cancel_order(tool_input["order_id"])
    
    try:
        content = json.dumps(content)
    except:
        content = str(content)

    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": content
            }
        ]
    }

def _extract_answer(content):
    return content[-1].text

@app.command()
def chat():
    # typer.echo(typer.style("Interactive mode - Type 'exit' to quit", fg=typer.colors.YELLOW))
    system_prompt = """
    You are a customer support agent for TechNova.
    """
    assistant_message = "TechNova Support: What would you like help with?"
    messages = []
    while True:
        q = input(assistant_message+"\n"+"===\n")
        if q.lower() == 'exit':
            break
        typer.echo(typer.style(f"User: {q}", fg=typer.colors.YELLOW))
        messages.append({"role": "user", "content": q})
        while True:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                system=system_prompt, 
                messages=messages,
                max_tokens=1000,
                tools=tools
            )
            messages.append({"role": "assistant", "content": response.content})
            typer.echo(typer.style(f"Assistant: {response.content}", fg=typer.colors.RED))
        
            if(response.stop_reason == "tool_use"):
                for c in response.content:
                    if c.type == "tool_use":
                        tool_response = process_tool_call(c)
                        typer.echo(typer.style(f"Tool Use: {tool_response['content'][0]['content']}", fg=typer.colors.BLUE))
                        messages.append(tool_response)
            else:
                assistant_message = _extract_answer(response.content)
                break

if __name__ == '__main__':
    app()