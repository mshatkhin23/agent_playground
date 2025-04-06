import wikipedia
import os

def get_stock_price(stock_symbol):
    return {"stock_symbol": stock_symbol, "stock_price": 100}

stock_price_tool_definition = {
    "name": "get_stock_price",
    "description": "Retrieves the current stock price for a given stock symbol",
    "input_schema": {
        "type": "object",
        "properties": {
            "stock_symbol": {
                "type": "string",
                "description": "The stock symbol to fetch stock data for"
            }
        },
        "required": ["stock_symbol"]
    }
}

def calculator(operation, num1, num2):
    if operation == "add":
        return num1 + num2
    elif operation == "subtract":
        return num1 - num2
    elif operation == "multiply":
        return num1 * num2
    elif operation == "divide": 
        if num2 == 0:
            return "Error: Division by zero"
        return num1 / num2
    else:
        return "Error: Invalid operation"

calculator_tool_definition = {
    "name": "calculator",
    "description": "Performs a mathematical operation on two numbers",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"], "description": "The operation to perform"},
            "num1": {"type": "number", "description": "The first number"},
            "num2": {"type": "number", "description": "The second number"}
        },
        "required": ["operation", "num1", "num2"]
    }
}

def add_to_research_file(research_topic, wikipedia_articles):
    output_file = "claude/output/research.md"
    if not os.path.exists(output_file):
        mode = "w"
    else:
        mode = "a"
    with open(output_file, mode) as f:
        f.write(f"## {research_topic}\n")
        for article in wikipedia_articles:
            f.write(f"* [{article['title']}]({article['url']}) \n")
        f.write("\n\n")

def wikipedia_helper(research_topic: str, article_titles: list[str], num_articles: int):
    wikipedia_articles = []
    if len(article_titles) > num_articles:
        article_titles = article_titles[:num_articles]
    for title in article_titles:
        results = wikipedia.search(title)
        try:
            page = wikipedia.page(results[0])
            title = page.title
            url = page.url
            wikipedia_articles.append({
                "title": title,
                "url": url,
            })
        except Exception as e:
            print(f"Error fetching Wikipedia article: {e}")
            continue
    add_to_research_file(research_topic, wikipedia_articles)


wikipedia_helper_tool_definition = {
    "name": "wikipedia_helper",
    "description": "Generates a list of Wikipedia articles for a given research topic",
    "input_schema": {
        "type": "object",
        "properties": {
            "research_topic": {"type": "string", "description": "The research topic to generate a Wikipedia reading list for"},
            "article_titles": {"type": "array", "description": "The list of article titles to generate a Wikipedia reading list for", "items": {"type": "string"}},
            "num_articles": {"type": "number", "description": "The number of articles to generate"}
        },
        "required": ["research_topic", "article_titles", "num_articles"]
    }
}

TOOLS = [stock_price_tool_definition, calculator_tool_definition, wikipedia_helper_tool_definition] 