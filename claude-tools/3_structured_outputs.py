import anthropic
import json
client = anthropic.Anthropic()


tools = [
    {
        "name": "print_sentiment_scores",
        "description": "Prints the sentiment scores for a given text",
        "input_schema": {
            "type": "object",
            "properties": {
                "positive_score": {
                    "type": "number",
                    "description": "The positive sentiment score for the text 0.0 to 1.0"
                },
                "negative_score": {
                    "type": "number",
                    "description": "The negative sentiment score for the text 0.0 to 1.0"
                },
                "neutral_score": {
                    "type": "number",
                    "description": "The neutral sentiment score for the text 0.0 to 1.0"
                }
            },
            "required": ["positive_score", "negative_score", "neutral_score"]
        }
    },
    {
        "name": "print_entities",
        "description": "Extracts the entities from the text",
        "input_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "description": "The entities from the text",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The entity name from the text"},
                            "type": {"type": "string", "description": "The type of entity (e.g. PERSON, LOCATION, ORGANIZATION, etc.)"},
                            "context": {"type": "string", "description": "The context of the entity in the text"}
                        }
                    }
                }
            },
            "required": ["entities"]
        }
    },
    {
        "name": "translate",
        "description": "Translates the text from English into other languages",
        "input_schema": {
            "type": "object",
            "properties": {
                "english": {
                    "type": "string", 
                    "description": "The original text in English"
                },
                "spanish": {
                    "type": "string",
                    "description": "The translated text in Spanish"
                },
                "french": {
                    "type": "string",
                    "description": "The translated text in French"
                },
                "japanese": {
                    "type": "string",
                    "description": "The translated text in Japanese"
                },
                "arabic": {
                    "type": "string",
                    "description": "The translated text in Arabic"
                },
                "chinese": {
                    "type": "string",
                    "description": "The translated text in Chinese"
                }
            },
            "required": ["english", "spanish", "french", "japanese", "arabic", "chinese"]
        }
    }

]

def get_sentiment(tweet: str):
    system_prompt = """
    Identify the sentiment of the text and print the sentiment scores - you must use the print_sentiment_scores tool to print the sentiment scores.
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        system=system_prompt,
        tools=tools,
        tool_choice={"type": "tool", "name": "print_sentiment_scores"},
        max_tokens=1000,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": tweet
            }
        ]
    )
    print(response)

def extract_entities(text: str):
    system_prompt = """
    Extract the entities from the text and print them - you must use the print_entities tool to print the entities.
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        system=system_prompt,
        tools=tools,
        tool_choice={"type": "tool", "name": "print_entities"},
        max_tokens=1000,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": text
            }
        ]
    )
    print(response)

def translate(english_text: str):
    system_prompt = """
    Translate the text from English into other languages. Use the translate tool.
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        system=system_prompt,
        tools=tools,
        tool_choice={"type": "tool", "name": "translate"},
        max_tokens=1000,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": english_text
            }
        ]
    )
    print(response)
    for c in response.content:
        if c.type == "tool_use" and c.name=="translate":
            try:
                print(json.dumps(c.input, ensure_ascii=False, indent=2))
            except:
                print(c.input)
            break

# get_sentiment("I'm a HUGE hater of pickles. I actually despise pickles. They are garbage")
# extract_entities("John works at Google in New York. He met with Sarah, the CEO of Acme Inc., last week in San Francisco.")
translate("how much does this cost?")