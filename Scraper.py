"""
GitHub Organization Governance Auditor
========================================

PURPOSE
-------
This script audits a GitHub organization's access-control structure to answer
one core compliance question:

    "Which repository admins are NOT registered as an approved department
    contact -- and for those that aren't, can we trace a path connecting
    them (via team or repo relationships) back to someone who IS?"

INPUT
-----
data-in/github-snapshot.json
    A single JSON snapshot expected to contain these top-level keys:
        - "repos"                 : list of repos, each with "full_name"
                                     and a "collaborators" list (each having
                                     "login" and an "admin" boolean flag)
        - "members"                : list of org members ("login", etc.)
        - "outside_collaborators"  : list of external collaborators
        - "teams"                  : list of teams, each with "id", "name",
                                     and a "members" list of {"login": ...}
        - "organization_roles"     : list of org-level role assignments

OUTPUT
------
All written to ./output/:
    repos.csv, members.csv, outside_collaborators.csv,
    teams.csv, organization_roles.csv     -- raw tabular exports of the JSON
    admin_users_teams.csv                 -- admins not matched to a contact
    member_contact_chain_report.csv       -- contact-chain result for every
                                              member/collaborator in the org
    github_governance_master_report.txt   -- full run log (tee'd from stdout),
                                              now including the pipeline's
                                              intermediate build summaries

KEY CONCEPTS
------------
- "Enterprise Admin" team (ID below): members are exempt from the audit,
  since they're expected to have admin rights everywhere by design.
- "Department Contacts" team (ID below): the set of "approved" contacts
  that every repo admin should be traceable back to.
- Contact chain: a BFS path from a given user to any department contact,
  walking two kinds of edges:
    1. Team edges   -- to fellow team members
    2. Repo edges   -- to a repo's admins, if the user has repo access
                       but isn't already an admin there
  This lets the audit flag not just "ungoverned" admins, but also whether
  they're at least indirectly reachable from an accountable contact.

NOTE ON LOGGING
---------------
Everything from Step 2 onward runs inside the `MasterLogger` context, so
every summary/debug print -- not just the final report sections -- is
captured in github_governance_master_report.txt as well as the console.
"""

import json
import os
import sys
import pandas as pd
from collections import deque


# ============================================================================
# Consolidated Stream Logger Engine
# ============================================================================
class MasterLogger:
    """
    Context manager that duplicates ('tees') all stdout output to both the
    terminal and a single consolidated report file.

    Everything printed inside a `with MasterLogger(...):` block becomes part
    of the permanent audit trail on disk, not just console output. Nearly
    the entire pipeline (map-building summaries + final report sections)
    now runs inside this block so the report file is a complete record of
    the run, not just the final sections.
    """

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
    """Return the lowercased set of member logins belonging to a given team ID."""
    team = df_teams[df_teams["id"] == team_id]
    if team.empty:
        return set()
    return {member["login"].lower() for member in team.iloc[0]["members"]}


def inspect(obj, indent=0, file=sys.stdout):
    """
    Recursively print the shape/schema of a nested dict/list structure
    (key names, container sizes, and leaf types) without dumping every
    value. Used purely as a structural sanity-check of the source JSON,
    printed at the top of the master report (Section 1).
    """
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
    """
    Breadth-first search for a path from `start_login` to any user in
    `contact_logins`, expanding via two relationship types:

      1. Team expansion: walk to every teammate of the current user.
      2. Repo expansion (fallback): if the current user has access to a
         repo but is NOT already an admin on it, walk to that repo's
         admins -- i.e. "who could vouch for/oversee this person's access."

    Returns the path as a list of logins (start -> ... -> contact), or
    None if no such path exists. Uses a `visited` set to avoid cycles;
    no depth cap is applied, so on very large/densely connected orgs this
    could be slow (though it will always terminate).
    """
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

    # ------------------------------------------------------------------
    # Step 1: Load the raw snapshot and flatten each section into a
    # DataFrame, exporting each as its own CSV for easy inspection.
    # This step runs BEFORE the logger opens since it's pure I/O setup
    # with nothing worth teeing to the report file.
    # ------------------------------------------------------------------
    with open(os.path.join("data-in", "github-snapshot.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    df_repos = pd.json_normalize(data["repos"])
    df_members = pd.json_normalize(data["members"])
    df_collabs = pd.json_normalize(data["outside_collaborators"])
    df_teams = pd.json_normalize(data["teams"])
    df_roles = pd.json_normalize(data["organization_roles"])

    df_repos.to_csv(os.path.join(output_dir, "repos.csv"), index=False)
    df_members.to_csv(os.path.join(output_dir, "members.csv"), index=False)
    df_collabs.to_csv(os.path.join(output_dir, "outside_collaborators.csv"), index=False)
    df_teams.to_csv(os.path.join(output_dir, "teams.csv"), index=False)
    df_roles.to_csv(os.path.join(output_dir, "organization_roles.csv"), index=False)

    # ========================================================================
    # Everything below (Steps 2-6) runs inside MasterLogger, so ALL of it --
    # including the intermediate build summaries -- lands in
    # github_governance_master_report.txt, not just the final report.
    # ========================================================================
    with MasterLogger("github_governance_master_report.txt"):
        print("======================================================================")
        print("                 GITHUB GOVERNANCE MASTER AUDIT REPORT                 ")
        print("======================================================================\n")

        # ------------------------------------------------------------------
        # Step 2: Build in-memory lookup maps in a single pass over teams
        # and repos. These form the "graph" that find_contact_chain() walks.
        #
        #   user_teams[login]   -> list of team-info dicts the user belongs to
        #   team_lookup[login]  -> list of lightweight {team_id, team_name}
        #   user_repos[login]   -> list of repo full_names the user can access
        #   repo_admins[repo]   -> set of logins with admin rights on that repo
        # ------------------------------------------------------------------
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

        # --- Debug/audit output: summarize the maps just built -------------
        print("----------------------------------------------------------------------")
        print("STEP 2: RELATIONSHIP MAP CONSTRUCTION SUMMARY")
        print("----------------------------------------------------------------------")
        print(f"user_teams   : {len(user_teams)} unique logins mapped to team memberships")
        print(f"team_lookup  : {len(team_lookup)} unique logins mapped to lightweight team refs")
        print(f"user_repos   : {len(user_repos)} unique logins mapped to repo access")
        print(f"repo_admins  : {len(repo_admins)} repos mapped to their admin sets")

        total_admin_slots = sum(len(admins) for admins in repo_admins.values())
        print(f"Total (repo, admin) pairs across the org: {total_admin_slots}\n")

        # Show a small sample of each map so you can sanity-check the shape
        sample_user = next(iter(user_teams), None)
        if sample_user:
            team_names = [t["team_name"] for t in user_teams[sample_user]]
            print(f"Sample -> user_teams['{sample_user}'] belongs to teams: {team_names}")

        sample_repo = next(iter(repo_admins), None)
        if sample_repo:
            print(f"Sample -> repo_admins['{sample_repo}'] = {sorted(repo_admins[sample_repo])}")
        print("\n")

        # ------------------------------------------------------------------
        # Step 3: Define the two reference groups the audit revolves around.
        #   - Enterprise Admins are exempt (expected to be admins everywhere).
        #   - Department Contacts are the "approved" set every admin should
        #     be traceable back to.
        # ------------------------------------------------------------------
        ENTERPRISE_ADMIN_TEAM_ID = 7597519
        DEPARTMENT_CONTACTS_TEAM_ID = 8752045

        ignored_logins = get_team_logins(df_teams, ENTERPRISE_ADMIN_TEAM_ID)
        contact_logins = get_team_logins(df_teams, DEPARTMENT_CONTACTS_TEAM_ID)

        # ------------------------------------------------------------------
        # Step 4: Build the flat list of (admin, repo, team) rows -- i.e.
        # "this person has admin rights on this repo, and belongs to this
        # team" -- excluding exempt enterprise admins.
        # ------------------------------------------------------------------
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

        # --- Debug/audit output: summarize the rows just built -------------
        print("----------------------------------------------------------------------")
        print("STEP 4: ADMIN-TO-TEAM ROW CONSTRUCTION SUMMARY")
        print("----------------------------------------------------------------------")
        print(f"Total (admin, repo, team) rows generated: {len(results)}")

        if not result_df.empty:
            unique_admins_seen = result_df["login"].nunique()
            unique_repos_seen = result_df["repo"].nunique()
            unique_teams_seen = result_df["team_id"].nunique()
            print(f"Unique non-exempt admins involved : {unique_admins_seen}")
            print(f"Unique repos involved              : {unique_repos_seen}")
            print(f"Unique teams involved               : {unique_teams_seen}")

            # Admins skipped because they're exempt enterprise admins
            all_repo_admin_logins = {
                login for admins in repo_admins.values() for login in admins
            }
            skipped_as_exempt = all_repo_admin_logins & ignored_logins
            print(f"Repo admins skipped as exempt (enterprise admins): {len(skipped_as_exempt)}")

            # Admins who are repo admins but have NO team at all -- these
            # silently produce zero rows (the inner `for team in ...` loop
            # never executes), which is worth flagging explicitly.
            admins_without_teams = {
                login for login in all_repo_admin_logins
                if login not in ignored_logins and not team_lookup.get(login)
            }
            if admins_without_teams:
                print(f"WARNING: {len(admins_without_teams)} non-exempt repo admins have "
                      f"NO team membership and were dropped from result_df entirely: "
                      f"{sorted(admins_without_teams)}")

            print("\nSample rows:")
            print(result_df.head(5).to_string(index=False))
        else:
            print("No (admin, repo, team) rows were generated -- result_df is empty.")
        print("\n")

        # ------------------------------------------------------------------
        # Step 5: Collect every known login across members + outside
        # collaborators, for the full org-wide chain check in Section 5.
        # ------------------------------------------------------------------
        all_logins = set()
        for df in [df_members, df_collabs]:
            if "login" in df.columns:
                all_logins.update(df["login"].dropna().str.lower())

        # --- Debug/audit output: summarize the identity pool just built ----
        print("----------------------------------------------------------------------")
        print("STEP 5: GLOBAL IDENTITY POOL CONSTRUCTION SUMMARY")
        print("----------------------------------------------------------------------")
        member_logins = (
            set(df_members["login"].dropna().str.lower()) if "login" in df_members.columns else set()
        )
        collab_logins = (
            set(df_collabs["login"].dropna().str.lower()) if "login" in df_collabs.columns else set()
        )

        print(f"Members with a login          : {len(member_logins)}")
        print(f"Outside collaborators w/ login : {len(collab_logins)}")
        print(f"Combined unique logins (all_logins): {len(all_logins)}")

        overlap = member_logins & collab_logins
        if overlap:
            print(f"NOTE: {len(overlap)} login(s) appear as BOTH a member and an "
                  f"outside collaborator: {sorted(overlap)}")

        # Flag if either source was missing a "login" column entirely --
        # this would silently contribute zero logins to the pool.
        if "login" not in df_members.columns:
            print("WARNING: df_members has no 'login' column -- members were skipped entirely.")
        if "login" not in df_collabs.columns:
            print("WARNING: df_collabs has no 'login' column -- outside collaborators were skipped entirely.")

        print(f"\nSample logins: {sorted(all_logins)[:5]}")
        print("\n")

        # ------------------------------------------------------------------
        # Step 6: Final report sections
        # ------------------------------------------------------------------

        # --- Section 1: confirm the shape of the source JSON -------------
        print("----------------------------------------------------------------------")
        print("SECTION 1: GITHUB SNAPSHOT SCHEMA STRUCTURAL AUDIT")
        print("----------------------------------------------------------------------")
        inspect(data)
        print("\n")

        # --- Section 2: who's exempt from this audit ----------------------
        print("----------------------------------------------------------------------")
        print("SECTION 2: EXEMPT ORGANIZATIONAL ENTERPRISE ADMINS")
        print("----------------------------------------------------------------------")
        print(f"Ignored Login Set Count: {len(ignored_logins)}")
        print(sorted(ignored_logins))
        print("\n")

        # --- Section 3: admins matched vs. unmatched to a contact ---------
        print("----------------------------------------------------------------------")
        print("SECTION 3: REPOSITORY ADMINISTRATOR VALIDATION & GAP METRICS")
        print("----------------------------------------------------------------------")
        print(f"Found {len(contact_logins)} registered department contacts.\n")

        unique_admins = result_df["login"].dropna().unique() if not result_df.empty else []
        found = [l for l in unique_admins if l.strip().lower() in contact_logins]
        not_found = [l for l in unique_admins if l.strip().lower() not in contact_logins]

        print(f"Admins with Matching Contact Entry ({len(found)}): {found}")
        print(f"Divergent Unassigned Administrators ({len(not_found)}): {not_found}\n")

        missing_admins_df = pd.DataFrame()
        if not result_df.empty:
            missing_admins_df = result_df[~result_df["login"].str.lower().isin(contact_logins)]
            print("Divergent Admin to Team Structural Matrix Mapping:")
            print(missing_admins_df[["login", "team_name"]].drop_duplicates().to_string(index=False))
            missing_admins_df.to_csv(os.path.join(output_dir, "admin_users_teams.csv"), index=False)
        print("\n")

        # --- Section 4: for each unmatched admin, try to trace a path -----
        # back to a department contact via team/repo relationships.
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

        # --- Section 5: same chain check, but for EVERY member/collaborator
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