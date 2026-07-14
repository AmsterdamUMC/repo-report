import json
import os
import sys
import pandas as pd
from collections import deque

# ============================================================================
# Consolidated Stream Logger Engine
# ============================================================================
class MasterLogger:
    """Redirects all stdout streams simultaneously to console and a single consolidated audit report file."""
    def __init__(self, filename="github_governance_master_report.txt"):
        self.filename = os.path.join("output", filename)
        self.terminal = sys.stdout
        self.log_file = None

    def __enter__(self):
        os.makedirs("output", exist_ok=True)
        self.log_file = open(self.filename, "w", encoding="utf-8")
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.terminal
        if self.log_file:
            self.log_file.close()

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()


def get_team_logins(df_teams, team_id):
    team = df_teams[df_teams["id"] == team_id]
    if team.empty:
        return set()
    return {member["login"].lower() for member in team.iloc[0]["members"]}


def inspect(obj, indent=0, file=sys.stdout):
    prefix = "  " * indent
    if isinstance(obj, dict):
        print(f"{prefix}dict ({len(obj)} keys)", file=file)
        for k, v in obj.items():
            print(f"{prefix}- {k}", file=file)
            inspect(v, indent + 1, file=file)
    elif isinstance(obj, list):
        print(f"{prefix}list ({len(obj)} items)", file=file)
        if obj:
            inspect(obj[0], indent + 1, file=file)
    else:
        print(f"{prefix}{type(obj).__name__}", file=file)


def find_contact_chain(start_login, contact_logins, user_teams, user_repos, repo_admins):
    start_login = start_login.lower()
    visited = {start_login}
    queue = deque([(start_login, [start_login])])

    while queue:
        current, path = queue.popleft()

        if current in contact_logins:
            return path

        # 1. Team Expansion Path
        for team in user_teams.get(current, []):
            for member in team["members"]:
                next_login = member["login"].lower()
                if next_login not in visited:
                    visited.add(next_login)
                    queue.append((next_login, path + [next_login]))

        # 2. Repo Access Expansion Path (Fallback)
        for repo_name in user_repos.get(current, []):
            admins = repo_admins.get(repo_name, set())
            if current not in admins:
                for next_login in admins:
                    if next_login not in visited:
                        visited.add(next_login)
                        queue.append((next_login, path + [next_login]))
    return None


# ============================================================================
# Core Pipeline Process
# ============================================================================
def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Load Source JSON
    with open(os.path.join("data-fer", "github-snapshot.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert to DataFrames
    df_repos = pd.json_normalize(data["repos"])
    df_members = pd.json_normalize(data["members"])
    df_collabs = pd.json_normalize(data["outside_collaborators"])
    df_teams = pd.json_normalize(data["teams"])
    df_roles = pd.json_normalize(data["organization_roles"])

    # Export Tabular Base Data
    df_repos.to_csv(os.path.join(output_dir, "repos.csv"), index=False)
    df_members.to_csv(os.path.join(output_dir, "members.csv"), index=False)
    df_collabs.to_csv(os.path.join(output_dir, "outside_collaborators.csv"), index=False)
    df_teams.to_csv(os.path.join(output_dir, "teams.csv"), index=False)
    df_roles.to_csv(os.path.join(output_dir, "organization_roles.csv"), index=False)

    # Single-Pass Relationships Map
    user_teams, team_lookup, user_repos, repo_admins = {}, {}, {}, {}

    for _, team in df_teams.iterrows():
        team_info = {"team_id": team["id"], "team_name": team["name"], "members": team["members"]}
        for member in team["members"]:
            login = member["login"].lower()
            user_teams.setdefault(login, []).append(team_info)
            team_lookup.setdefault(login, []).append({"team_id": team["id"], "team_name": team["name"]})

    for _, repo in df_repos.iterrows():
        repo_name = repo["full_name"]
        admins_set = set()
        for collab in repo["collaborators"]:
            login = collab["login"].lower()
            user_repos.setdefault(login, []).append(repo_name)
            if collab.get("admin", False):
                admins_set.add(login)
        repo_admins[repo_name] = admins_set

    # Define Fixed IDs
    ENTERPRISE_ADMIN_TEAM_ID = 7597519
    DEPARTMENT_CONTACTS_TEAM_ID = 8752045
    
    ignored_logins = get_team_logins(df_teams, ENTERPRISE_ADMIN_TEAM_ID)
    contact_logins = get_team_logins(df_teams, DEPARTMENT_CONTACTS_TEAM_ID)

    # Process Missing Repository Administrators List
    results = []
    for _, repo in df_repos.iterrows():
        repo_name = repo["full_name"]
        for admin_login in repo_admins.get(repo_name, set()):
            if admin_login in ignored_logins:
                continue
            for team in team_lookup.get(admin_login, []):
                results.append({
                    "login": admin_login,
                    "repo": repo_name,
                    "team_id": team["team_id"],
                    "team_name": team["team_name"]
                })
    result_df = pd.DataFrame(results)

    # Collect Global Identity Pool
    all_logins = set()
    for df in [df_members, df_collabs]:
        if "login" in df.columns:
            all_logins.update(df["login"].dropna().str.lower())

    # ========================================================================
    # EXECUTE CONSOLIDATED MASTER LOG WRITER
    # ========================================================================
    with MasterLogger("github_governance_master_report.txt"):
        print("======================================================================")
        print("                 GITHUB GOVERNANCE MASTER AUDIT REPORT                 ")
        print("======================================================================\n")

        print("----------------------------------------------------------------------")
        print("SECTION 1: GITHUB SNAPSHOT SCHEMA STRUCTURAL AUDIT")
        print("----------------------------------------------------------------------")
        inspect(data)
        print("\n")

        print("----------------------------------------------------------------------")
        print("SECTION 2: EXEMPT ORGANIZATIONAL ENTERPRISE ADMINS")
        print("----------------------------------------------------------------------")
        print(f"Ignored Login Set Count: {len(ignored_logins)}")
        print(sorted(ignored_logins))
        print("\n")

        print("----------------------------------------------------------------------")
        print("SECTION 3: REPOSITORY ADMINISTRATOR VALIDATION & GAP METRICS")
        print("----------------------------------------------------------------------")
        print(f"Found {len(contact_logins)} registered department contacts.\n")
        
        unique_admins = result_df["login"].dropna().unique() if not result_df.empty else []
        found = [l for l in unique_admins if l.strip().lower() in contact_logins]
        not_found = [l for l in unique_admins if l.strip().lower() not in contact_logins]

        print(f"Admins with Matching Contact Entry ({len(found)}): {found}")
        print(f"Divergent Unassigned Administrators ({len(not_found)}): {not_found}\n")
        
        if 1 == 1:
            if not result_df.empty:
                missing_admins_df = result_df[~result_df["login"].str.lower().isin(contact_logins)]
                print("Divergent Admin to Team Structural Matrix Mapping:")
                print(missing_admins_df[["login", "team_name"]].drop_duplicates().to_string(index=False))
                missing_admins_df.to_csv(os.path.join(output_dir, "admin_users_teams.csv"), index=False)
        else:
            missing_admins_df = pd.DataFrame()
        print("\n")

        print("----------------------------------------------------------------------")
        print("SECTION 4: TRANSITIVE TRANSVERSAL PATHWAYS (MISSING REPO ADMINS)")
        print("----------------------------------------------------------------------")
        admin_report = []
        if not missing_admins_df.empty:
            for login in missing_admins_df["login"].unique():
                path = find_contact_chain(login, contact_logins, user_teams, user_repos, repo_admins)
                admin_report.append({
                    "login": login,
                    "contact_path": " -> ".join(path) if path else "NOT FOUND"
                })
        admin_report_df = pd.DataFrame(admin_report)
        print(admin_report_df.to_string(index=False))
        print("\n")

        print("----------------------------------------------------------------------")
        print("SECTION 5: GLOBAL ACCOUNT IDENTITY MAP (MEMBERS & COLLABORATORS)")
        print("----------------------------------------------------------------------")
        print(f"Running full map checks across all {len(all_logins)} workspace entities...")
        full_report = []
        for login in sorted(all_logins):
            path = find_contact_chain(login, contact_logins, user_teams, user_repos, repo_admins)
            full_report.append({
                "login": login,
                "contact_chain": " -> ".join(path) if path else "NOT FOUND"
            })
        full_report_df = pd.DataFrame(full_report)
        full_report_df.to_csv(os.path.join(output_dir, "member_contact_chain_report.csv"), index=False)
        print("Unified identity routing tracking written successfully to output reports.")
        print("\n======================================================================")
        print("                     CONSOLIDATED RUN COMPLETE                         ")
        print("======================================================================")


if __name__ == "__main__":
    main()