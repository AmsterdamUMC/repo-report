

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
#print(all_root_repos)

print(f"\n2. Teams Mapping Sample (First 3 teams):")
for team_name, repos in list(team_repo_map.items())[:3]:
    print(f"   - {team_name}: {repos}")


print(f"\n3. Repositories NOT mentioned in any team ({len(unassigned_repos)} total):")
for repo in unassigned_repos:
    print(f"   - {repo}")





######################

import json

# Load your JSON data
with open("data-in/governance.clean.json ", "r") as file:
    data = json.load(file)

# ==========================================
# 1. CORE DATA EXTRACTION & MAPPING
# ==========================================

# Map every root repo to its list of collaborators: {repo_name: [login1, login2, ...]}
repo_collaborators = {}
all_root_repos = []

for repo in data.get("repos", []):
    repo_name = repo.get("full_name")
    if repo_name:
        all_root_repos.append(repo_name)
        # Extract logins of everyone explicitly added to this repo
        collaborators = [c["login"] for c in repo.get("collaborators", []) if "login" in c]
        repo_collaborators[repo_name] = collaborators

# Map every team to its list of repositories: {team_name: [repo1, repo2, ...]}
team_repo_map = {}
# Map every team to its members: {team_name: [login1, login2, ...]}
team_member_map = {}
# Reverse lookup: Map every user login to the teams they belong to: {login: [team1, team2, ...]}
user_teams_map = {}

for team in data.get("teams", []):
    team_name = team.get("name")
    if not team_name:
        continue
        
    # Extract repos for this team
    team_repos = [r["full_name"] for r in team.get("repos", []) if "full_name" in r]
    team_repo_map[team_name] = team_repos
    
    # Extract members for this team
    team_members = [m["login"] for m in team.get("members", []) if "login" in m]
    team_member_map[team_name] = team_members
    
    # Populate the reverse lookup (User -> Teams)
    for login in team_members:
        if login not in user_teams_map:
            user_teams_map[login] = []
        user_teams_map[login].append(team_name)


# ==========================================
# 2. UNASSIGNED REPO ANALYSIS & TEAM SEARCH
# ==========================================

# Find which repositories from root are completely missing from team allocations
all_assigned_repos = set(repo for repos in team_repo_map.values() for repo in repos)
unassigned_repos = [repo for repo in all_root_repos if repo not in all_assigned_repos]


# ==========================================
# 3. PRINTING THE RESULTS
# ==========================================

print("=== 1. WHO IS IN EACH REPOSITORY (COLLABORATORS) ===")
# Showing a sample of 3 repositories to keep console clean
for repo_name in all_root_repos[:3]:
    users = repo_collaborators.get(repo_name, [])
    print(f"Repo: {repo_name}")
    print(f"  Collaborators ({len(users)}): {', '.join(users) if users else 'None'}")

print("\n" + "="*50)
print("=== 2. ANALYSIS OF UNASSIGNED REPOSITORIES ===")
print(f"Found {len(unassigned_repos)} repositories not mapped to any team.\n")




def get_team_logins(teams, team_id):
    """Return the lowercased set of member logins belonging to a given team ID."""
    for team in teams:
        if team.get("id") == team_id:
            return {member["login"].lower() for member in team.get("members", [])}
    return set()

import json
import os
import pandas as pd
with open(os.path.join("data-in", "github-snapshot.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
ENTERPRISE_ADMIN_TEAM_ID = 7597519
DEPARTMENT_CONTACTS_TEAM_ID = 8752045
ignored_logins = get_team_logins(data["teams"], ENTERPRISE_ADMIN_TEAM_ID)
contact_logins = get_team_logins(data["teams"], DEPARTMENT_CONTACTS_TEAM_ID)




final_overview = {} 

for repo_name in unassigned_repos:
    print(f"Unassigned Repo: {repo_name}")
    collaborators = repo_collaborators.get(repo_name, [])
    print(f"  -> Direct Collaborators: {', '.join(collaborators) if collaborators else 'None'}")
    
    listt=[]
    # Cross-reference collaborator logins with team memberships
    found_any_team_link = False
    for login in collaborators:
        #print("login: ", login)
        #print(ignored_logins)
        if login in user_teams_map and login not in ignored_logins:
            found_any_team_link = True
            associated_teams = user_teams_map[login]
            print(f"     [!] Collaborator '{login}' belongs to Team(s): {', '.join(associated_teams)}")
            listt.append([login, associated_teams])
    if not found_any_team_link and collaborators:
        print("     [-] None of the direct collaborators belong to any defined Team.")
    print("-" * 30)

    final_overview[repo_name] = listt

#print(final_overview)

with open("demofile.csv", "w") as f:
    for dp in final_overview:
        f.write(f"{dp},{final_overview[dp]}\n")

