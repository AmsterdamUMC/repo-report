#```python
# 01.scrape-github.py
#
# Parallelized GitHub organization governance scraper.
#
# Produces:
# - data/github-snapshot.json
# - data/rest-api-logs.json
#
# Improvements:
# - Parallel repository scraping
# - Parallel team scraping
# - Parallel organization-role scraping
# - Thread-safe logging
# - Retry/backoff handling
# - Rate limit awareness
# - Eager pagination loading
#
# Recommended token scopes:
# - repo
# - read:org

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from github import Github
from github import Auth
from github.GithubException import GithubException

from shared import log_raw, get_request

# =========================================================
# Constants
# =========================================================

ORG_NAME = os.environ["RR_ORG_NAME"]
GITHUB_TOKEN = os.environ["RR_GITHUB_TOKEN"]
os.makedirs("data-fer", exist_ok=True) #TEST

# Tune based on org size / rate limits
MAX_REPO_WORKERS = 10
MAX_TEAM_WORKERS = 8
MAX_ROLE_WORKERS = 4

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

# =========================================================
# Globals
# =========================================================

org_out = {}
raw_out = []

raw_lock = Lock()

# =========================================================
# Helpers
# =========================================================


def thread_safe_log(raw_out, label, data):
    """
    Protect shared raw_out list from concurrent writes.
    """
    with raw_lock:
        log_raw(raw_out, label, data)


def wait_for_rate_limit(gh):
    """
    Sleep if rate limit is getting low.
    """
    try:
        rate = gh.get_rate_limit().core

        if rate.remaining < 100:
            sleep_time = max(rate.reset.timestamp() - time.time(), 0)

            print(
                f"[RATE LIMIT] Remaining={rate.remaining}. "
                f"Sleeping {sleep_time:.0f}s"
            )

            time.sleep(sleep_time + 1)

    except Exception as e:
        print(f"[WARN] Failed checking rate limit: {e}")


def retry(fn, *args, **kwargs):
    """
    Retry wrapper with exponential backoff.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)

        except GithubException as e:
            last_error = e

            wait_time = RETRY_BACKOFF_SECONDS * (2 ** attempt)

            print(
                f"[RETRY] {fn.__name__} failed "
                f"(attempt {attempt + 1}/{MAX_RETRIES}) "
                f"sleeping {wait_time}s: {e}"
            )

            time.sleep(wait_time)

    raise last_error


# =========================================================
# Repo Scraper
# =========================================================


def scrape_repo(repo_in):
    """
    Scrape one repository.
    """
    print(f"[REPO] {repo_in.full_name}")

    thread_safe_log(raw_out, "org_in.get_repos()", repo_in)

    repo_out = {
        "full_name": repo_in.full_name,
        "visibility": repo_in.visibility,
        "collaborators": [],
    }

    try:
        collaborators = retry(repo_in.get_collaborators)

        for collaborator_in in collaborators:
            thread_safe_log(
                raw_out,
                "repo_in.get_collaborators()",
                collaborator_in,
            )

            permissions = collaborator_in.permissions

            repo_out["collaborators"].append(
                {
                    "login": collaborator_in.login,
                    "admin": permissions.admin,
                    "maintain": permissions.maintain,
                    "push": permissions.push,
                    "triage": permissions.triage,
                    "pull": permissions.pull,
                }
            )

    except Exception as e:
        print(f"[ERROR] Repo {repo_in.full_name}: {e}")

    return repo_out


# =========================================================
# Team Scraper
# =========================================================


def scrape_team(team_in):
    """
    Scrape one team.
    """
    print(f"[TEAM] {team_in.name}")

    thread_safe_log(raw_out, "org_in.get_teams()", team_in)

    team_out = {
        "id": team_in.id,
        "name": team_in.name,
        "parent": None,
        "members": [],
        "repos": [],
    }

    try:
        if team_in.parent is not None:
            team_out["parent"] = {
                "id": team_in.parent.id,
                "name": team_in.parent.name,
            }

        # ============================================
        # Members
        # ============================================

        members = retry(team_in.get_members)

        for member_in in members:
            try:
                thread_safe_log(
                    raw_out,
                    "team_in.get_members()",
                    member_in,
                )

                membership = retry(
                    team_in.get_team_membership,
                    member_in,
                )

                thread_safe_log(
                    raw_out,
                    "team_in.get_team_membership(member_in)",
                    membership,
                )

                team_out["members"].append(
                    {
                        "login": member_in.login,
                        "role": membership.role,
                        "state": membership.state,
                    }
                )

            except Exception as e:
                print(
                    f"[ERROR] Team member "
                    f"{team_in.name}/{member_in.login}: {e}"
                )

        # ============================================
        # Repos
        # ============================================

        repos = retry(team_in.get_repos)

        for repo_in in repos:
            try:
                thread_safe_log(
                    raw_out,
                    "team_in.get_repos()",
                    repo_in,
                )

                permission = retry(
                    team_in.get_repo_permission,
                    repo_in,
                )

                thread_safe_log(
                    raw_out,
                    "team_in.get_repo_permission(repo_in)",
                    permission,
                )

                team_out["repos"].append(
                    {
                        "full_name": repo_in.full_name,
                        "admin": (
                            permission.admin
                            if permission is not None
                            else None
                        ),
                        "maintain": (
                            permission.maintain
                            if permission is not None
                            else None
                        ),
                        "push": (
                            permission.push
                            if permission is not None
                            else None
                        ),
                        "triage": (
                            permission.triage
                            if permission is not None
                            else None
                        ),
                        "pull": (
                            permission.pull
                            if permission is not None
                            else None
                        ),
                    }
                )

            except Exception as e:
                print(
                    f"[ERROR] Team repo "
                    f"{team_in.name}/{repo_in.full_name}: {e}"
                )

    except Exception as e:
        print(f"[ERROR] Team {team_in.name}: {e}")

    return team_out


# =========================================================
# Organization Role Scraper
# =========================================================


def scrape_org_role(org_role_in):
    """
    Scrape one organization role.
    """
    role_id = org_role_in["id"]

    print(f"[ROLE] {org_role_in['name']}")

    org_role_out = {
        "id": role_id,
        "name": org_role_in["name"],
        "teams": [],
        "users": [],
    }

    try:
        # ============================================
        # Teams
        # ============================================

        teams_in = retry(
            get_request,
            gh,
            f"/orgs/{ORG_NAME}/organization-roles/{role_id}/teams",
        )

        thread_safe_log(
            raw_out,
            f"organization-role/{role_id}/teams",
            teams_in,
        )

        for team_in in teams_in.raw_data:
            org_role_out["teams"].append(
                {
                    "id": team_in["id"],
                    "name": team_in["name"],
                }
            )

        # ============================================
        # Users
        # ============================================

        users_in = retry(
            get_request,
            gh,
            f"/orgs/{ORG_NAME}/organization-roles/{role_id}/users",
        )

        thread_safe_log(
            raw_out,
            f"organization-role/{role_id}/users",
            users_in,
        )

        for user_in in users_in.raw_data:
            org_role_out["users"].append(
                {
                    "id": user_in["id"],
                    "login": user_in["login"],
                }
            )

    except Exception as e:
        print(f"[ERROR] Organization role {role_id}: {e}")

    return org_role_out


# =========================================================
# Main
# =========================================================

print("[START] Connecting to GitHub")

auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)

# =========================================================
# Organization
# =========================================================

org_in = gh.get_organization(ORG_NAME)

thread_safe_log(
    raw_out,
    "gh.get_organization(ORG_NAME)",
    org_in,
)

# =========================================================
# Repositories
# =========================================================

print("[LOAD] Fetching repositories")

repos_in = list(org_in.get_repos())

print(f"[INFO] Loaded {len(repos_in)} repos")

org_out["repos"] = []

with ThreadPoolExecutor(max_workers=MAX_REPO_WORKERS) as executor:
    futures = [
        executor.submit(scrape_repo, repo_in)
        for repo_in in repos_in
    ]

    for future in as_completed(futures):
        try:
            org_out["repos"].append(future.result())
        except Exception as e:
            print(f"[ERROR] Repo future failed: {e}")

# =========================================================
# Members
# =========================================================

print("[LOAD] Fetching organization members")

members_in = list(org_in.get_members())

print(f"[INFO] Loaded {len(members_in)} members")

org_out["members"] = []

for member_in in members_in:
    try:
        print(f"[MEMBER] {member_in.login}")

        thread_safe_log(
            raw_out,
            "org_in.get_members()",
            member_in,
        )

        membership = retry(
            member_in.get_organization_membership,
            ORG_NAME,
        )

        thread_safe_log(
            raw_out,
            "member_in.get_organization_membership(ORG_NAME)",
            membership,
        )

        org_out["members"].append(
            {
                "login": member_in.login,
                "role": membership.role,
                "state": membership.state,
            }
        )

    except Exception as e:
        print(f"[ERROR] Member {member_in.login}: {e}")

# =========================================================
# Outside Collaborators
# =========================================================

print("[LOAD] Fetching outside collaborators")

outside_collaborators_in = list(
    org_in.get_outside_collaborators()
)

print(
    f"[INFO] Loaded "
    f"{len(outside_collaborators_in)} outside collaborators"
)

org_out["outside_collaborators"] = []

for collaborator_in in outside_collaborators_in:
    try:
        print(f"[OUTSIDE] {collaborator_in.login}")

        thread_safe_log(
            raw_out,
            "org_in.get_outside_collaborators()",
            collaborator_in,
        )

        org_out["outside_collaborators"].append(
            {
                "login": collaborator_in.login,
            }
        )

    except Exception as e:
        print(
            f"[ERROR] Outside collaborator "
            f"{collaborator_in.login}: {e}"
        )

# =========================================================
# Teams
# =========================================================

print("[LOAD] Fetching teams")

teams_in = list(org_in.get_teams())

print(f"[INFO] Loaded {len(teams_in)} teams")

org_out["teams"] = []

with ThreadPoolExecutor(max_workers=MAX_TEAM_WORKERS) as executor:
    futures = [
        executor.submit(scrape_team, team_in)
        for team_in in teams_in
    ]

    for future in as_completed(futures):
        try:
            org_out["teams"].append(future.result())
        except Exception as e:
            print(f"[ERROR] Team future failed: {e}")

# =========================================================
# Organization Roles
# =========================================================

print("[LOAD] Fetching organization roles")

org_roles_in = retry(
    get_request,
    gh,
    f"/orgs/{ORG_NAME}/organization-roles",
)

thread_safe_log(
    raw_out,
    f"get_request('/orgs/{ORG_NAME}/organization-roles')",
    org_roles_in,
)

roles = org_roles_in.raw_data["roles"]

print(f"[INFO] Loaded {len(roles)} organization roles")

org_out["organization_roles"] = []

with ThreadPoolExecutor(max_workers=MAX_ROLE_WORKERS) as executor:
    futures = [
        executor.submit(scrape_org_role, role)
        for role in roles
    ]

    for future in as_completed(futures):
        try:
            org_out["organization_roles"].append(
                future.result()
            )
        except Exception as e:
            print(f"[ERROR] Role future failed: {e}")

# =========================================================
# Write Output
# =========================================================

print("[WRITE] Writing github snapshot")

os.makedirs("data-fer", exist_ok=True)
with open("data-fer/github-snapshot.json", "w") as f:
    json.dump(org_out, f, indent=2)

print("[WRITE] Writing raw API logs")

with open("data-fer/rest-api-logs.json", "w") as f:
    json.dump(raw_out, f, indent=2)

# =========================================================
# Done
# =========================================================

print("[DONE]")

gh.close()
#```
