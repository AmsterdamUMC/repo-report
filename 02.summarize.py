# 02.summarize.py
#
import json, pandas as pd

# *** Summarize the governance data into a set of tables
with open('data/governance.clean.json') as f:
    governance_json = json.load(f)

# Repos
repos_df = pd.json_normalize(
    governance_json['repos'],
    'collaborators',
    ['full_name']
)
repos_df.to_csv('data/governance.repos.csv', index=False)

# Members
members_df = pd.json_normalize(
    governance_json['members']
)
repos_df.to_csv('data/governance.members.csv', index=False)

# Outside collaborators
outside_collaborators_df = pd.json_normalize(
    governance_json['outside_collaborators']
)
outside_collaborators_df.to_csv('data/governance.outside_collaborators.csv', index=False)

# Teams by members
teams_members_df = pd.json_normalize(
    governance_json['teams'],
    'members',
    ['name']
)
teams_members_df.to_csv('data/governance.teams_members.csv', index=False)

# Teams by repositories
teams_repos_df = pd.json_normalize(
    governance_json['teams'],
    'repos',
    ['name']
)
teams_repos_df.to_csv('data/governance.teams_repos.csv', index=False)

# Organization roles by teams
organization_roles_teams_df = pd.json_normalize(
    governance_json['organization_roles'],
    'teams',
    ['name']    
)
organization_roles_teams_df.to_csv('data/governance.organization_roles_teams.csv', index=False)

# Organization roles by users
organization_roles_users_df = pd.json_normalize(
    governance_json['organization_roles'],
    'users',
    ['name']    
)
organization_roles_users_df.to_csv('data/governance.organization_roles_users.csv', index=False)

