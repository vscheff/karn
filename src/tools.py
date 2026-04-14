tools = [
    {
        "type": "web_search"
    },
    {
        "type": "function",
        "name": "generate",
        "description": "Generates an image and sends it to the channel",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Prompt used to generate the image"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "type": "function",
        "name": "card",
        "description": "Sends the image of a Magic: the Gathering card and it's price to the channel",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name of the MtG card"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "image",
        "description": "Searches the web for an image and sends one or more results to the channel",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query used to search for the image(s)"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of images to return"
                }
            },
            "required": ["query", "count"]
        }
    },
    {
        "type": "function",
        "name": "weather",
        "description": "Fetches and returns the live weather forecast for a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location to retrieve weather for. The location can be specified in any of the following formats: city; city, state; zipcode."
                    }
                },
            "required": ["location"]
        }
    },
    {
        "type": "function",
        "name": "remind",
        "description": "Sets a reminder with a specified time and message. When the specified time is reached, the user will be pinged with the specified message",
        "parameters": {
            "type": "object",
            "properties": {
                "when": {
                    "type": "string",
                    "description": "The date and time at which the user will receive the reminder. This can be an absolute date and time (i.e. \"07/26/2026 16:20\"), or it can be a relative time (i.e. \"tomorrow at 4:20pm\")."
                    },
                "message": {
                    "type": "string",
                    "description": "The message that will be sent to the user at the specified date and time. This can include Discord-style user tags (i.e. \"<@Von\")."
                    }
                },
            "required": ["when", "message"]
        }
    },
    {
        "type": "function",
        "name": "readme",
        "description": "Retrieves information on this bot's current capabilities, implemented commands (both slash and prefix), and other functionalities. This will give an explanation of all implementented commands, how to use them, any flags associated with the command, and any aliases for the command. Additionally, this function will explain all other functionalities beyond the commands that the bot has implemented (i.e. the rating system or the hat system). Call this function anytime a user is asking about commands the bot has, how to use the commands, or if a user is asking what the capabilities of the bot are."
    },
]

FUNC_INIT = 10
PROP_INIT = 3
PROP_KEY = 3
ENUM_INIT = -3
ENUM_ITEM = 3
FUNC_END = 12


def get_tool_token_cost(tools, encoding):
    if not tools:
        return 0

    num_tokens = 0

    for tool in tools:
        if tool["type"] != "function":
            continue
            
        num_tokens += FUNC_INIT + FUNC_END + len(encoding.encode(f"{tool['name']}:{tool['description'].rstrip('.')}"))
        
        if "parameters" not in tool or not len(tool["parameters"]["properties"]):
            continue

        num_tokens += PROP_INIT

        for key, val in tool["parameters"]["properties"].items():
            num_tokens += PROP_KEY
            
            if "enum" in val.keys():
                num_tokens += ENUM_INIT

                for item in val["enum"]:
                    num_tokens += ENUM_ITEM + len(encoding.encode(item))

            num_tokens += len(encoding.encode(f"{key}:{val['type']}:{val['description'].rstrip('.')}"))

        num_tokens += FUNC_END

    return num_tokens
