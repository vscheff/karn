tools = [
    {
        "type": "function",
        "name": "generate",
        "description": "Generates an image",
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
        "description": "Returns the image of a Magic: the Gathering card.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name of the MtG card"
                }
            },
            "required": ["query"]
        },
        "output_mode": "tool_only"
    },
    {
        "type": "function",
        "name": "image",
        "description": "Searches the web for an image and returns one or more results",
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
        num_tokens += FUNC_INIT + FUNC_END + len(encoding.encode(f"{tool['name']}:{tool['description'].rstrip('.')}"))
        
        if not len(tool["parameters"]["properties"]):
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
