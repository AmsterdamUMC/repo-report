import json
import os
import hashlib
import argparse
from collections import defaultdict

FILES = [
    "data-in/github-snapshot.json",
    "data-in/governance.clean.json",
    "data-in/governance.raw.json",
    "data-in/rest-api-logs.json"
]

OUTPUT_FILE = "output/json_structure_report.md"

SENSITIVE = [
    "email", "billing", "token", "secret", 
    "password", "authorization", "key"
]

os.makedirs("output", exist_ok=True)

def type_name(v):
    """Converts standard Python objects/primitives into human-readable strings."""
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int): return "integer"
    if isinstance(v, float): return "number"
    if isinstance(v, str): return "string"
    return type(v).__name__

def analyze(v, name="root", depth=0, output=None):
    """Recursively walks a JSON object to map its nested structure to Markdown."""
    indent = "    " * depth
    if isinstance(v, dict):
        output.write(f"{indent}- **{name}**: object\n")
        for k, child in v.items():
            analyze(child, k, depth + 1, output)
    elif isinstance(v, list):
        output.write(f"{indent}- **{name}**: array ({len(v)} items)\n")
        if v:
            analyze(v[0], "item", depth + 1, output)
    else:
        output.write(f"{indent}- **{name}**: {type_name(v)}\n")

examples = defaultdict(set)

def collect_examples(v, path="root"):
    """Collects up to 5 unique string examples for every nested field path."""
    if isinstance(v, dict):
        for k, child in v.items():
            collect_examples(child, f"{path}.{k}")
    elif isinstance(v, list):
        for item in v[:5]:
            collect_examples(item, path)
    else:
        if len(examples[path]) < 5:
            examples[path].add(str(v))

def write_examples(output):
    """Writes compiled scalar data examples out to the report stream."""
    output.write("\n## Examples\n\n")
    for field, values in examples.items():
        output.write(f"### {field}\n")
        for value in values:
            output.write(f"- `{value}`\n")
        output.write("\n")

def find_sensitive(v, path="root"):
    """Searches keys for keywords matching potential PII or authentication details."""
    result = []
    if isinstance(v, dict):
        for k, child in v.items():
            current = f"{path}.{k}"
            if any(x in k.lower() for x in SENSITIVE):
                result.append(current)
            result.extend(find_sensitive(child, current))
    elif isinstance(v, list) and v:
        result.extend(find_sensitive(v[0], path))
    return result

def skeleton(v):
    """Strips variable data out of the JSON, leaving a structural blueprint."""
    if isinstance(v, dict):
        return {k: skeleton(x) for k, x in v.items()}
    if isinstance(v, list):
        return [skeleton(v[0])] if v else []
    return type_name(v)

def schema_id(v):
    """Generates an 8-character unique hash representing the schema layout structure."""
    data = json.dumps(skeleton(v), sort_keys=True)
    return hashlib.md5(data.encode()).hexdigest()[:8]

def write_stats(filename, data, output):
    """Computes file properties and basic runtime payload diagnostics."""
    output.write("## Stats\n\n")
    output.write(f"- Size: {os.path.getsize(filename)/1024:.2f} KB\n")
    output.write(f"- Root: {type_name(data)}\n")
    if isinstance(data, dict):
        output.write(f"- Fields: {len(data)}\n")
    if isinstance(data, list):
        output.write(f"- Records: {len(data)}\n")
    output.write("\n")

def main():
    # 1. Setup the command line arguments configuration
    parser = argparse.ArgumentParser(description="Analyze JSON schemas and generate structural reports.")
    parser.add_argument("--stats", action="store_true", help="Include file statistics")
    parser.add_argument("--structure", action="store_true", help="Include nested structural blueprint mapping")
    parser.add_argument("--examples", action="store_true", help="Include raw content examples profiling")
    parser.add_argument("--sensitive", action="store_true", help="Include security and PII risk assessment scans")
    parser.add_argument("--schema", action="store_true", help="Include schema identification grouping hashes")
    args = parser.parse_args()

    # 2. Determine if user selected specific flags. If no flags are passed, run everything.
    user_flags = [args.stats, args.structure, args.examples, args.sensitive, args.schema]
    run_all = not any(user_flags)

    schemas = {}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as report:
        report.write("# JSON Structure Report\n")

        for filename in FILES:
            if not os.path.exists(filename):
                print(f"Skipping missing file: {filename}")
                continue

            with open(filename) as f:
                data = json.load(f)

            report.write(f"\n---\n\n# {filename}\n\n")
            
            # --- Conditionals handling toggled execution stages ---
            if run_all or args.stats:
                write_stats(filename, data, report)

            if run_all or args.structure:
                report.write("## Structure\n\n")
                analyze(data, output=report)

            if run_all or args.examples:
                examples.clear()
                collect_examples(data)
                write_examples(report)

            if run_all or args.sensitive:
                report.write("## Sensitive Fields\n\n")
                sensitive = find_sensitive(data)
                if sensitive:
                    for item in sensitive:
                        report.write(f"- ⚠ `{item}`\n")
                else:
                    report.write("None detected\n")

            if run_all or args.schema:
                sid = schema_id(data)
                report.write(f"\n## Schema\n\n`{sid}`\n")
                schemas.setdefault(sid, []).append(filename)

        # Output Summary showing which files share identical formats
        if run_all or args.schema:
            report.write("\n---\n\n# Schema Groups\n\n")
            for sid, files in schemas.items():
                report.write(f"## {sid}\n\n")
                for file in files:
                    report.write(f"- {file}\n")

    print(f"Created: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()