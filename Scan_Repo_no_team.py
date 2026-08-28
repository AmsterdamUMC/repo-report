

from collections import Counter
import json

with open("data-in/governance.clean.json ", "r") as file:
    data = json.load(file)


# --- Task 1: Create a list of all root/repos/full_name ---
# Uses a set instead of a list for O(1) lookups in Task 3
all_root_repos = [repo["full_name"] for repo in data.get("repos", []) if "full_name" in repo]


# --- Task 2: Create a dict {team_name: [repo_full_name, ...]} ---
team_repo_map = {}

for team in data.get("teams", []):
    team_name = team.get("name")
    
    # Extract all repo names assigned to this specific team
    team_repos = [repo["full_name"] for repo in team.get("repos", []) if "full_name" in repo]
    
    # Store in the dictionary
    team_repo_map[team_name] = team_repos


# --- Task 3: Check what names in the root list are NOT mentioned in the dict ---
# First, collect every unique repo name that belongs to AT LEAST one team
all_assigned_repos = set()
for repos_list in team_repo_map.values():
    all_assigned_repos.update(repos_list)

# Compare the root list against the assigned set
unassigned_repos = [repo for repo in all_root_repos if repo not in all_assigned_repos]


# --- Print Results ---
print(f"1. Total Root Repositories Found: {len(all_root_repos)}")

print(all_root_repos)

print(f"\n2. Teams Mapping Sample (First 3 teams):")
for team_name, repos in list(team_repo_map.items())[:3]:
    print(f"   - {team_name}: {repos}")


print(f"\n3. Repositories NOT mentioned in any team ({len(unassigned_repos)} total):")
for repo in unassigned_repos:
    print(f"   - {repo}")