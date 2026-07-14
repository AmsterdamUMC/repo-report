import os
import json
from github import Github

ORG_NAME = os.environ["ORG_NAME"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

gh = Github(GITHUB_TOKEN, per_page=100)

org = gh.get_organization(ORG_NAME)


def process_repo(repo):
    result = {
        "full_name": repo.full_name,
        "commits": []
    }

    try:
        commits = repo.get_commits()

        for i, commit in enumerate(commits):
            if i >= 200:   # prevents abuse + huge API usage
                break

            data = commit.raw_data

            result["commits"].append({
                "sha": data["sha"],
                "parents": [
                    {"sha": p["sha"]}
                    for p in data.get("parents", [])
                ],
                "author_login": data.get("author", {}).get("login"),
                "commit_author_name": data.get("commit", {}).get("author", {}).get("name"),
                "commit_committer_name": data.get("commit", {}).get("committer", {}).get("name")
            })

    except Exception as e:
        result["error"] = str(e)

    return result


repos = list(org.get_repos())

results = [process_repo(repo) for repo in repos]

os.makedirs("data", exist_ok=True)

with open("data/provenance_fer.clean.json", "w") as f:
    json.dump(results, f, indent=2)

gh.close()