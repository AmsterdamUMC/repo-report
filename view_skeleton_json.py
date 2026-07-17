import json

def skeleton(obj):
    if isinstance(obj, dict):
        return {k: skeleton(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        if obj:
            return [skeleton(obj[0])]
        else:
            return []
    elif isinstance(obj, str):
        return "string"
    elif isinstance(obj, bool):
        return "boolean"
    elif isinstance(obj, int):
        return "integer"
    elif isinstance(obj, float):
        return "number"
    elif obj is None:
        return "null"
    else:
        return type(obj).__name__

import json

files = [
    "data-in/github-snapshot.json",
    "data-in/governance.clean.json",
    "data-in/governance.raw.json",
    "data-in/rest-api-logs.json"
]

for filename in files:
    print("\n====================")
    print(filename)
    print("====================")

    with open(filename) as f:
        data = json.load(f)

    print(json.dumps(skeleton(data), indent=2))