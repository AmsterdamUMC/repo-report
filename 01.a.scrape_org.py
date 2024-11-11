# 01.scrape_org.py
#
# Scrape the governance structure of a GitHub organization by collecting information about:
# - Each repo, and per repo, its collaborators
# - Each organization member
# - Each outside collaborator
# - Each team, and per team, its permissions for the repos of that team
# 
# Thomas Pronk, 2024-11-11

# Libraries
import os, json
from github import Github
from github import Auth

# Globals
org_name = 'AmsterdamUMC'

# Copying raw responses from PyGitHub to a dict
def dictify_response(source):
    return {
        'raw_data': source.raw_data,
        'raw_headers': source.raw_headers
    }

# Login to GitHub
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
gh = Github(auth=auth)

# Process the current organization
org_in = gh.get_organization(org_name)
org_out = {}

# # Process each repo of the current organization
org_out['repos'] = []
for repo_in in org_in.get_repos():
    repo_out = {
        'full_name': repo_in.full_name,
        'collaborators': []
    }
    for collaborator_in in repo_in.get_collaborators():
        repo_out['collaborators'].append({
            'login': collaborator_in.login,
            'role': collaborator_in.role,
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
    membership_in = member_in.get_organization_membership(org_name)
    org_out['members'].append({
        'login': member_in.login,
        'role': membership_in.role,
        'state': membership_in.state
    })

# Process each outside collaborator of the organization
org_out['outside_collaborators'] = []
for outside_collaborator_in in org_in.get_outside_collaborators():
    org_out['outside_collaborators'].append({
        'login': outside_collaborator_in.login
    })

# Process each team of the current organization
org_out['teams'] = []
for team_in in org_in.get_teams():
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
        membership_in = team_in.get_team_membership(member_in)
        team_out['members'].append({
            'login': member_in.login,
            'role': membership_in.role,
            'state': membership_in.state
        })
    # Process each repo of the current team
    for repo_in in team_in.get_repos():
        permission_in = team_in.get_repo_permission(repo_in)
        team_out['repos'].append({
            'full_name': repo_in.full_name,
            'admin': permission_in.admin,
            'maintain': permission_in.maintain,
            'push': permission_in.push,
            'triage': permission_in.triage,
            'pull': permission_in.pull
        })

    org_out['teams'].append(team_out)

# Wrap up repodata
print(json.dumps(org_out, indent = 2))
with open('data-out/org_out.json', 'w') as f:
    json.dump(org_out, f, indent = 2)

# Close connections
gh.close()


