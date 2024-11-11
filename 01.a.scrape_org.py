# 01.scrape_org.py
#
# Scrape the governance structure of a GitHub organization by collecting information about:
# - Each repo, and per repo, its collaborators
# - Each organization member
# - Each outside collaborator
# - Each team, and per team, its permissions for the repos of that team
# The variable `org_out` contains the main data on the governance structure, while `raw_out` contains detailed information on each request/response made to construct `org_out`
#
# Thomas Pronk, 2024-11-11

# Libraries
import os, json
from github import Github
from github import Auth

# Globals
org_name = 'AmsterdamUMC'
org_out = {}
raw_out = []

# Login to GitHub
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
gh = Github(auth=auth)

# Process the current organization
org_in = gh.get_organization(org_name)
log_raw('gh.get_organization(org_name)', org_in)

# Log a raw request
def log_raw(request, result):
    raw_result = {
        'request': request,
        'raw_data': result.raw_data,
        'raw_headers': result.raw_headers,
    }
    print(json.dumps(raw_result, indent = 2))
    raw_out.append(raw_result)


# Process each repo of the current organization
org_out['repos'] = []
for repo_in in org_in.get_repos():
    log_raw('org_in.get_repos()', repo_in)
    repo_out = {
        'full_name': repo_in.full_name,
        'collaborators': []
    }
    # Process each collaborator of the current repo
    for collaborator_in in repo_in.get_collaborators():
        log_raw('repo_in.get_collaborators()', collaborator_in)
        repo_out['collaborators'].append({
            'login': collaborator_in.login,
            'admin': collaborator_in.permissions.admin,
            'maintain': collaborator_in.permissions.maintain,
            'push': collaborator_in.permissions.push,
            'triage': collaborator_in.permissions.triage,
            'pull': collaborator_in.permissions.pull      
        })
    org_out['repos'].append(repo_out)

# Process each member of the organization
org_out['members'] = []
for member_in in org_in.get_members():
    log_raw('org_in.get_members()', member_in)    
    organization_membership_in = member_in.get_organization_membership(org_name)
    log_raw('member_in.get_organization_membership(org_name)', organization_membership_in)    
    org_out['members'].append({
        'login': member_in.login,
        'role': organization_membership_in.role,
        'state': organization_membership_in.state
    })

# Process each outside collaborator of the organization
org_out['outside_collaborators'] = []
for outside_collaborator_in in org_in.get_outside_collaborators():
    log_raw('org_in.get_outside_collaborators()', outside_collaborator_in)    
    org_out['outside_collaborators'].append({
        'login': outside_collaborator_in.login
    })

# Process each team of the current organization
org_out['teams'] = []
for team_in in org_in.get_teams():
    log_raw('org_in.get_teams()', team_in)
    team_out = {
        'name': team_in.name,
        'id': team_in.id,
        'parent': None,
        'members': [],
        'repos': []
    }
    if team_in.parent is not None:
        team_out['parent'] = {
            'name': team_in.parent.name,
            'id': team_in.parent.id,
        }
    
    # Process each member of the current team
    for member_in in team_in.get_members():
        log_raw('team_in.get_members()', member_in)
        team_membership_in = team_in.get_team_membership(member_in)
        log_raw('team_in.get_team_membership(member_in)', team_membership_in)
        team_out['members'].append({
            'login': member_in.login,
            'role': team_membership_in.role,
            'state': team_membership_in.state
        })

    # Process each repo of the current team
    for repo_in in team_in.get_repos():
        log_raw('team_in.get_repos()', repo_in)
        permission_in = team_in.get_repo_permission(repo_in)
        log_raw('team_in.get_repo_permission(repo_in)', permission_in)
        team_out['repos'].append({
            'full_name': repo_in.full_name,
            'admin': permission_in.admin,
            'maintain': permission_in.maintain,
            'push': permission_in.push,
            'triage': permission_in.triage,
            'pull': permission_in.pull
        })

    org_out['teams'].append(team_out)

# Wrap up 
print(json.dumps(org_out, indent = 2))
with open('data-out/org_out.json', 'w') as f:
    json.dump(org_out, f, indent = 2)
with open('data-out/raw_out.json', 'w') as f:
    json.dump(raw_out, f, indent = 2)

# Close connections
gh.close()


