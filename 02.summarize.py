# 02.summarize.py
#
import json, pandas as pd

# *** Summarize the governance data into a set of tables
with open('data/governance.clean.json') as f:
    governance_json = json.load(f)

# Repos
df_collaborators = pd.json_normalize(
    governance_json['repos'],
    'collaborators',
    ['full_name']
)
# Number of collaborators per repo
df_n_repo_user_total = \
    df_collaborators[['full_name', 'login']]. \
    groupby('full_name', as_index=False). \
    count(). \
    rename(columns={'login': 'user_total'})


df_n_repo_user_roles = \
    df_collaborators[['full_name', 'admin', 'maintain', 'push', 'triage', 'pull']]. \
    groupby('full_name', as_index=False). \
    sum(). \
    rename(columns={'admin': 'user_admin', 'maintain': 'user_maintain', 'push': 'user_push', 'triage': 'user_triage', 'pull': 'user_pull'})

# Members
df_members = pd.json_normalize(
    governance_json['members']
)

# Outside collaborators
df_ocs = pd.json_normalize(
    governance_json['outside_collaborators']
)

# How many members and outside collaborators are collaborators on each repo?
df_n_repo_members = df_members. \
    merge(df_collaborators, how='inner') \
    [['full_name', 'login']]. \
    groupby('full_name', as_index=False). \
    count(). \
    rename(columns={'login': 'member_total'})

df_n_repo_ocs = df_ocs. \
    merge(df_collaborators, how='inner') \
    [['full_name', 'login']]. \
    groupby('full_name', as_index=False). \
    count(). \
    rename(columns={'login': 'oc_total'})   


# Teams by members
df_teams_members = pd.json_normalize(
    governance_json['teams'],
    'members',
    ['name']
)

# Teams by repositories
df_teams_repos = pd.json_normalize(
    governance_json['teams'],
    'repos',
    ['name']
)

# Number of teams per repo
df_n_repo_teams = df_teams_repos \
    [['full_name', 'name']]. \
    groupby('full_name', as_index=False). \
    count(). \
    rename(columns={'name': 'team_total'})

# Merge all repo summary variables together
df_n_repo_summary = df_n_repo_user_total. \
    merge(df_n_repo_user_roles, how='left'). \
    merge(df_n_repo_members, how='left'). \
    merge(df_n_repo_ocs, how='left'). \
    merge(df_n_repo_teams, how='left')
    
# Organization roles by teams
df_organization_roles_teams = pd.json_normalize(
    governance_json['organization_roles'],
    'teams',
    ['name']    
)
df_organization_roles_teams.to_csv('data/governance.organization_roles_teams.csv', index=False)

# Organization roles by users
df_organization_roles_users = pd.json_normalize(
    governance_json['organization_roles'],
    'users',
    ['name']    
)
df_organization_roles_users.to_csv('data/governance.organization_roles_users.csv', index=False)

