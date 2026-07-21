import json
import os
from datetime import datetime, timezone
import pandas as pd
from pandas.errors import ParserError
import csv

# 📁 Configured Asset Slugs
SNAPSHOT_FILE = "data-in/github-snapshot.json"
GOVERNANCE_FILE = "data-in/governance.clean.json"
RAW_GOV_FILE = "data-in/governance.raw.json"
RAW_LOGS_FILE = "data-in/rest-api-logs.json"
AUDIT_REPORT = "output/github_governance_audit.md"

#Manual_Member_overview = "data-in/members-joined.tsv"
Manual_Member_overview = "data/member-contact-information.tsv.csv"

#"data/members-joined" vs data-in/github-snapshot.json/members
#                         data-in/governance.clean.json/members


os.makedirs("output", exist_ok=True)

def load_json(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None
        
def load_tsv(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_csv(filepath, sep="\t", encoding="utf-8")
    except (ParserError, UnicodeDecodeError):
        return None

def load_csv(filepath):
    if not os.path.exists(filepath):
        print("path not found")
        return None
    try:
        users=[]
        with open(filepath, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                print(row[3])
                users.append(row[3])
                
                #print(row)
        #print("@@@")
        #print("hallo")
        return users
        #return pd.read_csv(filepath)
    except (ParserError, UnicodeDecodeError):
        return None

def run_audit():
    snapshot = load_json(SNAPSHOT_FILE) or {}
    governance = load_json(GOVERNANCE_FILE) or {}
    raw_gov = load_json(RAW_GOV_FILE) or []
    logs = load_json(RAW_LOGS_FILE) or []
    manual_members = load_csv(Manual_Member_overview)
    #manual_members.head()
    print("HALLO")
    print(manual_members)


    # Current execution operational timeline baseline (mid-2026 anchor window)
    current_date = datetime(2026, 7, 17, tzinfo=timezone.utc)
    
    # Extract structural root entries safely
    repos = snapshot.get("repos", [])
    teams = snapshot.get("teams", [])
    outside_collabs = snapshot.get("outside_collaborators", [])
    members = snapshot.get("members", []) #can also be governance

    org_raw_data = raw_gov[0].get("raw_data", {}) if isinstance(raw_gov, list) and len(raw_gov) > 0 else {}

    with open(AUDIT_REPORT, "w", encoding="utf-8") as out:
        out.write("# 🛡️ Automated Enterprise GitHub Governance Analysis\n\n")
        out.write(f"_Audit Executed Chronologically on: `{current_date.strftime('%Y-%m-%d %H:%M:%S')} UTC`_\n\n")

        # =====================================================================
        # FER. NEW IMPLEMNT
        # =====================================================================
        #print(members)
        out.write("##  0. GitHub Username \n")
        out.write("Flags ......\n\n")
        out.write("| GitHub User Name | Report | Explain |\n")
        out.write("| :--- | :--- |\n")
        
        for member in members:
            #acitve = member.get('state'==acitve, [])
            print(member)
            member_name = member.get("login")
            if member.get("state") == "active":
                if member.get("login") in manual_members:
                    pass #member ok                    
                else:
                    out.write(f"| `{f'member/{member_name}'.ljust(25)}` | `{'MISSING'.ljust(8)}` | `member missing from member contact sheet` |\n")
            elif member.get("state") == "inactive":
                if member.get("login") in manual_members:
                    out.write(f"| `{f'member/{member_name}'.ljust(25)}` | `{'INACTIVE'.ljust(8)}` | `member has to be send to inactive members` |\n")
                else:
                    pass #CHeck if in inacative members


        # =====================================================================
        # 1. THE "BUS FACTOR" ASSIGNMENT MONITOR
        # =====================================================================
        out.write("## ⚠️ 1. Single Point of Failure Analysis (Bus Factor = 1)\n")
        out.write("Identifies workflows or repositories controlled exclusively by a single account.\n\n")
        
        bus_factor_teams = []
        for team in teams:
            team_members = team.get("members", [])
            if len(team_members) == 1:
                bus_factor_teams.append((team.get("name", "Unnamed Team"), team_members[0].get("login", "Unknown")))
                
        if bus_factor_teams:
            out.write("| Vulnerable Team Node | Single Owner Keyholder |\n")
            out.write("| :--- | :--- |\n")
            for t_name, user in bus_factor_teams:
                out.write(f"| `teams/{t_name}` | `{user}` 🚨 |\n")
        else:
            out.write("- ✅ All core internal teams maintain distributed multi-member ownership structures.\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 2. DEFAULT BRANCH STANDARDIZATION
        # =====================================================================
        out.write("## 🌿 2. Default Branch Naming Compliance\n")
        out.write("Flags projects retaining obsolete default branch nomenclature (e.g., `master`, `dev`).\n\n")
        
        non_standard_branches = []
        for repo in repos:
            def_branch = repo.get("default_branch", "main")
            if def_branch != "main":
                non_standard_branches.append((repo.get("full_name"), def_branch))
                
        if non_standard_branches:
            out.write("| Non-Compliant Workspace | Detected Active Branch Target | Suggested Remediated State |\n")
            out.write("| :--- | :--- | :--- |\n")
            for r_name, branch in non_standard_branches:
                out.write(f"| {r_name} | `{branch}` | Move target to `main` |\n")
        else:
            out.write("- ✅ 100% compliance across organizational default branches (`main`).\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 3. PRIVATE FORK EXPOSURE WATCHDOG
        # =====================================================================
        out.write("## 🔓 3. Data Leak Prevention: Private Fork Policy\n")
        
        fork_allowed = org_raw_data.get("members_can_fork_private_repositories", False)
        if fork_allowed:
            out.write("### 🚨 CRITICAL THREAT: PRIVATE FORKING IS ENABLED\n")
            out.write("Internal staff can copy proprietary company code assets into unmanaged personal storage buckets.\n")
        else:
            out.write("- ✅ **Private Repository Fork Protection:** Enforced. Codebase containment intact.\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 4. WEBHOOK SECURITY ASSESSMENT
        # =====================================================================
        out.write("## 🔗 4. Webhook Security & Sign-off Integrity\n")
        
        webhook_exposed = False
        # Simulating processing nested parameters from webhook collections
        for repo in repos:
            # If data profile flags exposed hooks without verification secrets
            if repo.get("has_unsecured_webhooks", False):
                webhook_exposed = True
                out.write(f"- ⚠️ Unauthenticated integration listener detected on repository: `{repo.get('full_name')}`\n")
                
        if not webhook_exposed:
            out.write("- ✅ All outward webhook routing nodes run secure validation signatures.\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 5. GHOST REPOSITORY ANALYSIS
        # =====================================================================
        out.write("## 👻 5. Inactive Sprawl Identification (> 180 Days)\n")
        
        ghost_repos = []
        for repo in repos:
            last_activity = repo.get("pushed_at") or repo.get("updated_at")
            if last_activity:
                try:
                    clean_ts = last_activity.replace("Z", "+00:00")
                    parsed_dt = datetime.fromisoformat(clean_ts)
                    days_idle = (current_date - parsed_dt).days
                    if days_idle > 180:
                        ghost_repos.append((repo.get("full_name"), days_idle))
                except ValueError:
                    continue

        if ghost_repos:
            out.write("| Stagnant Codebase Hub | Days Dormant | Recommended Operational Action |\n")
            out.write("| :--- | :--- | :--- |\n")
            for r_name, days in sorted(ghost_repos, key=lambda x: x[1], reverse=True):
                out.write(f"| {r_name} | {days} Days | `Archive / Deprecate Asset` |\n")
        else:
            out.write("- ✅ Zero stagnant shadow codebases active.\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 6. EXTERNAL ROLE PRIVILEGE ESCALATION MATRIX
        # =====================================================================
        out.write("## 👥 6. Outside Collaborator Blast Radius Map\n")
        
        outside_logins = {c["login"] for c in outside_collabs if "login" in c}
        escalated_externals = []
        
        for repo in repos:
            for person in repo.get("collaborators", []):
                user_id = person.get("login")
                if user_id in outside_logins:
                    if person.get("admin") or person.get("push"):
                        access_tier = "Administrative Owner" if person.get("admin") else "Direct Write Contributor"
                        escalated_externals.append((user_id, repo.get("full_name"), access_tier))

        if escalated_externals:
            out.write("| External Contributor Account | Workspace Context | Privilege Scope Assignment |\n")
            out.write("| :--- | :--- | :--- |\n")
            for user, r_name, tier in escalated_externals:
                out.write(f"| `{user}` | {r_name} | **{tier}** 🚨 |\n")
        else:
            out.write("- ✅ Outside access matrix metrics remain locked to read-only views.\n")
        out.write("\n---\n\n")

        # =====================================================================
        # 7. RESOURCE COMPLIANCE DRIFT
        # =====================================================================
        out.write("## 🔄 7. Asset Registration Status (Drift Summary)\n")
        
        snap_repos = {r["full_name"] for r in repos if "full_name" in r}
        gov_repos = {r["full_name"] for r in governance.get("repos", []) if "full_name" in r}
        unmanaged_items = snap_repos - gov_repos

        out.write(f"- Live Assets Tracked: **{len(snap_repos)}**\n")
        out.write(f"- Declarative Registries Logged: **{len(gov_repos)}**\n")
        if unmanaged_items:
            out.write("\n### Untracked Repositories Requiring Official Sign-off:\n")
            for item in sorted(unmanaged_items):
                out.write(f"- `[UNREGISTERED]` **{item}**\n")
        else:
            out.write("- ✅ Configuration schemas run completely in-sync.\n")
        out.write("\n---\n\n")

       # =====================================================================
        # 8. VELOCITY TREND CONSUMPTION ANALYSIS (UPGRADED)
        # =====================================================================
        out.write("## 📊 8. API Velocity Exhaustion Profile\n")
        
        max_pool = None
        rem_pool = None
        headers_found = False

        # 1. Normalize logs into a loopable list even if it's a single dictionary
        log_entries = []
        if isinstance(logs, list):
            log_entries = logs
        elif isinstance(logs, dict):
            log_entries = [logs]

        if log_entries:
            # 2. Look backwards from the most recent logs to find valid headers
            for entry in reversed(log_entries):
                raw_headers = entry.get("raw_headers", {})
                
                # 3. Handle case-insensitivity (GitHub often outputs lowercase headers)
                normalized_headers = {str(k).lower(): str(v) for k, v in raw_headers.items()}
                
                max_pool = normalized_headers.get("x-ratelimit-limit")
                rem_pool = normalized_headers.get("x-ratelimit-remaining")
                
                if max_pool and rem_pool:
                    headers_found = True
                    break # Success! Found the metrics.

            if headers_found:
                try:
                    lim_int = int(max_pool)
                    rem_int = int(rem_pool)
                    used_pct = ((lim_int - rem_int) / lim_int) * 100 if lim_int > 0 else 0
                    
                    out.write(f"- **Hourly App Pool Space:** {lim_int} requests\n")
                    out.write(f"- **Token Space Remaining:** {rem_int} requests\n")
                    out.write(f"- **Quota Volatility Curve:** `{used_pct:.2f}%` spent during current sync loop.\n")
                except (ValueError, TypeError) as e:
                    out.write(f"- ⚠️ Found headers but couldn't parse values: Limit=`{max_pool}`, Remaining=`{rem_pool}`\n")
            else:
                out.write("- ⚠️ Could not find standard `x-ratelimit-limit` or `x-ratelimit-remaining` keys inside the logged headers.\n")
        else:
            out.write("- ⚠️ Integration API historical tracking stream file is empty or unreadable.\n")
    print(f"🎉 Executive Governance Dashboard generated at: {AUDIT_REPORT}")

if __name__ == "__main__":
    run_audit()