import json
import os
import pandas as pd
# ============================================================================
# Helper functions
# ============================================================================
def get_team_logins(df_teams, team_id):
    team = df_teams[df_teams["id"] == team_id]
    if team.empty:
        return set()
    return {
        member["login"].lower()
        for member in team.iloc[0]["members"]
    }

# ============================================================================
# Load GitHub snapshot
# ============================================================================
with open(os.path.join("data-fer","github-snapshot.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

def inspect(obj, indent=0):
    prefix = "  " * indent
    if isinstance(obj, dict):
        print(f"{prefix}dict ({len(obj)} keys)")
        for k, v in obj.items():
            print(f"{prefix}- {k}")
            inspect(v, indent + 1)
            #break  # remove break to inspect all keys

    elif isinstance(obj, list):
        print(f"{prefix}list ({len(obj)} items)")
        if obj:
            inspect(obj[0], indent + 1)

    else:
        print(f"{prefix}{type(obj).__name__}")
inspect(data)

# ============================================================================
# Convert JSON structures into DataFrames   # json_normalize() converts the nested JSON into tabular structures.
# The snapshot contains:    # - repos   # - members    # - outside_collaborators    # - teams   # - organization_roles
# ============================================================================
print("#########################")
df_repos = pd.json_normalize(data["repos"])
df_members = pd.json_normalize(data["members"])
df_collabs = pd.json_normalize(data["outside_collaborators"])
df_teams = pd.json_normalize(data["teams"])
df_roles = pd.json_normalize(data["organization_roles"])

#for name, df in {
#    "repos": df_repos,
#    "members": df_members,
#    "outside_collaborators": df_collabs,
#    "teams": df_teams,
#    "organization_roles": df_roles,
#}.items():
#    print(f"\n{name}")
#    print(f"rows={len(df)}, cols={len(df.columns)}")
#    print(df.columns.tolist())

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
df_repos.to_csv(os.path.join(output_dir, "repos.csv"), index=False)
df_members.to_csv(os.path.join(output_dir, "members.csv"), index=False)
df_collabs.to_csv(os.path.join(output_dir, "outside_collaborators.csv"), index=False)
df_teams.to_csv(os.path.join(output_dir, "teams.csv"), index=False)
df_roles.to_csv(os.path.join(output_dir, "organization_roles.csv"), index=False)

# ============================================================================
# Build ignore list: Members of the Owners team are organization administrators and should not  be reported as missing department contacts.
# ============================================================================
#IGNORE ADMINS #ENTERPRISE_ADMIN_TEAM_ID = 7597519 
ignored_logins = get_team_logins(df_teams, 7597519)   
print("Ignored logins:")
print(sorted(ignored_logins))

# ============================================================================
# Find repository administrators: Iterate through all repositories and collect collaborators that have admin permissions.
# Result: login -> repository -> team
# ============================================================================
# Build login -> teams lookup
team_lookup = {}
for _, team in df_teams.iterrows():
    for member in team["members"]:
        team_lookup.setdefault(member["login"], []).append({
            "team_id": team["id"],
            "team_name": team["name"]
        })

# Find admins and their teams
results = []
for _, repo in df_repos.iterrows():
    for collab in repo["collaborators"]:

        if not collab.get("admin", False):
            continue

        login = collab["login"]

        if login.lower() in ignored_logins:
            continue

        for team in team_lookup.get(login, []):
            results.append({
                "login": login,
                "repo": repo["full_name"],
                "team_id": team["team_id"],
                "team_name": team["team_name"]
            })

result_df = pd.DataFrame(results)

print("WOW")
print(result_df)
# ============================================================================
# Department Contacts validation
# Department Contacts are considered the official responsible contacts
# for repositories and teams.
# Compare repository administrators against members of the Department
# Contacts team.
# ============================================================================
#DEPARTMENT_CONTACTS_TEAM_ID = 8752045
contact_logins = get_team_logins(df_teams, 8752045)   # Department Contacts
print(f"Found {len(contact_logins)} department contacts")
print(sorted(contact_logins))
# Create a set of known GitHub usernames
known_users = contact_logins
found = []
not_found = []

for login in result_df["login"].dropna().unique():

    if login.strip().lower() in known_users:
        found.append(login)
    else:
        not_found.append(login)

print(f"Found: {len(found)}")
print(found)
print(f"\nNot found: {len(not_found)}")
print(not_found)

missing_admins = result_df[
    ~result_df["login"].str.lower().isin(known_users)
]

print(missing_admins[["login", "team_name"]].drop_duplicates())
missing_admins.to_csv(
    "output/admin_users_teams.csv",
    index=False
)

# ============================================================================
# Contact path discovery
# For administrators that are not Department Contacts:
# The first Department Contact found is reported.
# ============================================================================
#Checking whether each repo had an admin, and this admin can be traced to a Department Team (i.e., listed in Amsterdam UMC. GitHub Department Contacts.xlsx) 

user_teams = {}
for _, team in df_teams.iterrows():
    for member in team["members"]:
        login = member["login"].lower()
        user_teams.setdefault(login, []).append({
            "team_id": team["id"],
            "team_name": team["name"],
            "members": team["members"]
        })
def find_contact_path(login, contact_logins, user_teams):
    """
    Find a chain from a GitHub user to a Department Contact.
    Uses breadth-first search (BFS) through team memberships.
    """
    login = login.lower()
    visited = set()
    queue = [(login, [login])]

    while queue:
        current, path = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        if current in contact_logins:
            return path
        for team in user_teams.get(current, []):
            for member in team["members"]:
                next_login = member["login"].lower()
                if next_login not in visited:
                    queue.append(
                        (next_login, path + [next_login])
                    )
    return None
report = []

for login in missing_admins["login"].unique():
    path = find_contact_path(
    login,
    contact_logins,
    user_teams,
    )
    report.append({
        "login": login,
        "contact_path": " -> ".join(path) if path else "NOT FOUND"
    })

report_df = pd.DataFrame(report)
print(report_df)






#Checking whether each member can be traced to a Department Team 
#Guessing what Department Teams the Outside Collaborators can be associated with, based on the repos they have access to. 


user_repos = {}
for _, repo in df_repos.iterrows():
    repo_name = repo["full_name"]

    for collab in repo["collaborators"]:
        login = collab["login"].lower()

        user_repos.setdefault(login, []).append(repo_name)


clean_repos = {}
for _, repo in df_repos.iterrows():
    clean_repos[repo["full_name"]] = [
        c["login"].lower()
        for c in repo["collaborators"]
    ]

repo_admins = {}
for _, repo in df_repos.iterrows():
    repo_admins[repo["full_name"]] = {
        c["login"].lower()
        for c in repo["collaborators"]
        if c.get("admin", False)
    }

from collections import deque
from collections import deque

def find_contact_chain(start_login, contact_logins, user_teams, user_repos):

    start_login = start_login.lower()

    visited = set()
    queue = deque([(start_login, [start_login])])

    while queue:

        current, path = queue.popleft()

        if current in visited:
            continue
        visited.add(current)

        if current in contact_logins:
            return path

        # -------------------------
        # 1. TEAM EXPANSION (PRIORITY)
        # -------------------------
        for team in user_teams.get(current, []):
            for member in team["members"]:

                if member.get("role") in ["maintainer", "admin"]:
                    next_login = member["login"].lower()

                    if next_login not in visited:
                        queue.append((next_login, path + [next_login]))

        # -------------------------
        # 2. REPO EXPANSION (WEAKER)
        # -------------------------
        for repo_name in user_repos.get(current, []):

            admins = repo_admins.get(repo_name, set())

            # ONLY expand IF current is NOT already admin
            if current not in admins:

                for next_login in admins:

                    if next_login not in visited:
                        queue.append((next_login, path + [next_login]))

    return None

all_logins = set()

for df in [df_members, df_collabs]:
    col = "login"

    if "login" not in df.columns:
        continue

    for login in df[col].dropna():
        all_logins.add(login.lower())
report = []


for login in all_logins:

    path = find_contact_chain(
        login,
        contact_logins,
        user_teams,
        user_repos
    )

    report.append({
        "login": login,
        "contact_chain": " -> ".join(path) if path else "NOT FOUND"
    })

report_df = pd.DataFrame(report)

report_df.to_csv(
    "output/member_contact_chain_report.csv",
    index=False
)