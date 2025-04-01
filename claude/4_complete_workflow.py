import wikipedia
from anthropic import Anthropic
import typer
import re

def get_article(search_term):
    results = wikipedia.search(search_term)
    first_result = results[0]
    page = wikipedia.page(first_result, auto_suggest=False)
    return page.content

article_search_tool = {
    "name": "get_article",
    "description": "A tool to retrieve an up to date Wikipedia article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "search_term": {
                "type": "string",
                "description": "The search term to find a wikipedia article by title"
            },
        },
        "required": ["search_term"]
    }
}

client = Anthropic()
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"

def _call_get_article(tool_use):
    search_term = tool_use.input["search_term"]
    wiki_result = get_article(search_term)
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": wiki_result
            }
        ]
    }

def _extract_answer(content):
    for c in content:
        if c.type == "text":
            # Extract text between <answer> tags
            match = re.search(r'<answer>(.*?)</answer>', c.text)
            if match:
                return match.group(1)
    return None

def answer_question(question):
    system_prompt = """
    You will be asked a question by the user. 
    If answering the question requires data you were not trained on, you can use the get_article tool to get the contents of a recent wikipedia article about the topic. 
    If you can answer the question without needing to get more information, please do so. 
    Only call the tool when needed. 
    """
    prompt = f"""
    Answer the following question <question>{question}</question>
    When you can answer the question, keep your answer as short as possible and enclose it in <answer> tags
    """
    messages = [{"role": "user", "content": prompt}]
    typer.echo(typer.style(f"User: {question}", fg=typer.colors.BLUE))

    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            system=system_prompt, 
            messages=messages,
            max_tokens=1000,
            tools=[article_search_tool]
        )
        messages.append({"role": "assistant", "content": response.content})
    
        if(response.stop_reason == "tool_use"):
            for c in response.content:
                if c.type == "tool_use" and c.name == "get_article":
                    typer.echo(typer.style(f"Claude wants to get an article about {c.input['search_term']}", fg=typer.colors.GREEN))
                    tool_response = _call_get_article(c)
                    messages.append(tool_response)
        else:
            answer = _extract_answer(response.content)
            typer.echo(typer.style(f"Final answer: {answer}", fg=typer.colors.MAGENTA))
            break

app = typer.Typer()

@app.command()
def main(question: str = "", interactive: bool = False):
    if interactive:
        typer.echo(typer.style("Interactive mode - Type 'exit' to quit", fg=typer.colors.YELLOW))
        while True:
            q = input("\nWhat would you like to ask? ")
            if q.lower() == 'exit':
                break
            answer_question(q)
    else:
        answer_question(question)

if __name__ == '__main__':
    app()