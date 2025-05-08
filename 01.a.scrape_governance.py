# 01.a.scrape_governance.py
#
# Scrape the governance structure of a GitHub organization by collecting information about each:
# - Repository
# - Organization member and outside collaborator
# - Team
# - Organization role

# The script produces two files:
# * `data-out/org_out.json`, which contains the organization snapshot. See details of this file below.
# * `data-out/raw_out.json`, which contains raw headers and data for each request made by the script to the GitHUB REST API. 

# Thomas Pronk, 2024-11-20

# *** Libraries
import os, json
from github import Github
from github import Auth
from shared import log_raw, get_request

# *** Constants
ORG_NAME = os.environ['ORG_NAME']
# Classic token with scopes: repo, reead:org
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

# *** Globals
org_out = {}
raw_out = []

# *** Main

# Login to GitHub
auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)

# Process the current organization
org_in = gh.get_organization(ORG_NAME)
log_raw(raw_out, 'gh.get_organization(ORG_NAME)', org_in)

# Process each repo of the current organization
org_out['repos'] = []
for repo_in in org_in.get_repos():
    log_raw(raw_out, 'org_in.get_repos()', repo_in)
    repo_out = {
        'full_name': repo_in.full_name,
        'collaborators': []
    }
    # Process each collaborator of the current repo
    for collaborator_in in repo_in.get_collaborators():
        log_raw(raw_out, 'repo_in.get_collaborators()', collaborator_in)
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
    log_raw(raw_out, 'org_in.get_members()', member_in)    
    organization_membership_in = member_in.get_organization_membership(ORG_NAME)
    log_raw(raw_out, 'member_in.get_organization_membership(ORG_NAME)', organization_membership_in)    
    org_out['members'].append({
        'login': member_in.login,
        'role': organization_membership_in.role,
        'state': organization_membership_in.state
    })
    if (member_in.login == 'tpronk-tester'):
        print('mark')
    

# Process each outside collaborator of the organization
org_out['outside_collaborators'] = []
for outside_collaborator_in in org_in.get_outside_collaborators():
    log_raw(raw_out, 'org_in.get_outside_collaborators()', outside_collaborator_in)    
    org_out['outside_collaborators'].append({
        'login': outside_collaborator_in.login
    })

# Process each team of the current organization
org_out['teams'] = []
for team_in in org_in.get_teams():
    log_raw(raw_out, 'org_in.get_teams()', team_in)
    team_out = {
        'id': team_in.id,
        'name': team_in.name,
        'parent': None,
        'members': [],
        'repos': []
    }
    if team_in.parent is not None:
        team_out['parent'] = {
            'id': team_in.parent.id,            
            'name': team_in.parent.name
        }
    
    # Process each member of the current team
    for member_in in team_in.get_members():
        log_raw(raw_out, 'team_in.get_members()', member_in)
        team_membership_in = team_in.get_team_membership(member_in)
        log_raw(raw_out, 'team_in.get_team_membership(member_in)', team_membership_in)
        team_out['members'].append({
            'login': member_in.login,
            'role': team_membership_in.role,
            'state': team_membership_in.state
        })

    # Process each repo of the current team
    for repo_in in team_in.get_repos():
        log_raw(raw_out, 'team_in.get_repos()', repo_in)
        permission_in = team_in.get_repo_permission(repo_in)
        log_raw(raw_out, 'team_in.get_repo_permission(repo_in)', permission_in)
        team_out['repos'].append({
            'full_name': repo_in.full_name,
            'admin': permission_in.admin if permission_in is not None else None,
            'maintain': permission_in.maintain if permission_in is not None else None,
            'push': permission_in.push if permission_in is not None else None,
            'triage': permission_in.triage if permission_in is not None else None,
            'pull': permission_in.pull if permission_in is not None else None
        })

    org_out['teams'].append(team_out)

# Process each organization role. Per organization role, list which teams and users have that role.
org_out['organization_roles'] = []
org_roles_in = get_request(gh, '/orgs/' + ORG_NAME + '/organization-roles')
log_raw(raw_out, "get_request('/orgs/' + ORG_NAME + '/organization-roles')", org_roles_in)
for org_role_in in org_roles_in.raw_data['roles']:
    org_role_out = {
        'id': org_role_in['id'],
        'name': org_role_in['name'],
        'teams': [],
        'users': []
    }

    teams_in = get_request(gh, '/orgs/' + ORG_NAME + '/organization-roles/' + str(org_role_in['id']) + '/teams')
    log_raw(raw_out, "get_request('/orgs/' + ORG_NAME + '/organization-roles/' + str(org_role_in['id']) + '/teams')", teams_in)
    for team_in in teams_in.raw_data:
        org_role_out['teams'].append({
            'id': team_in['id'],
            'name': team_in['name']
        })

    users_in = get_request(gh, '/orgs/' + ORG_NAME + '/organization-roles/' + str(org_role_in['id']) + '/users')
    log_raw(raw_out, "get_request('/orgs/' + ORG_NAME + '/organization-roles/' + str(org_role_in['id']) + '/users')", users_in)
    for user_in in users_in.raw_data:
        org_role_out['users'].append({
            'id': user_in['id'],
            'login': user_in['login']
        })

    org_out['organization_roles'].append(org_role_out)

# Wrap up 
print(json.dumps(org_out, indent = 2))
with open('data-in/governance.clean.json', 'w') as f:
    json.dump(org_out, f, indent = 2)
with open('data-in/governance.raw.json', 'w') as f:
    json.dump(raw_out, f, indent = 2)

# Close connections
gh.close()


