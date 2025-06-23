# 02.a.summarize_repos.py

import math, json, pandas as pd
pd.options.display.max_rows = 2000

# Read governance snapshot
with open('data-in/governance.clean.json') as f:
    governance_json = json.load(f)


# *** Construct df_ossociates
# df_members; table of members
df_members = pd.json_normalize(
    governance_json['members']
)[['login', 'role']]
# df_ocs; table outside collaborators
df_ocs = pd.json_normalize(
    governance_json['outside_collaborators']
) 
df_ocs['role'] = 'oc'
# df_ossociates; a table of members and outside collaborators, identified via role:
# member = normal member, admin = organization owner, oc = outside collaborator
df_associates = pd.concat([df_members, df_ocs], ignore_index=True)


# *** Construct df_departments
# df_teams_members; each row is a membership of user X with team Y 
df_teams_members = pd.json_normalize(
    governance_json['teams'],
    'members',
    ['name']
)
# df_department_contacts; Department Contacts
df_department_contacts = pd \
    .read_csv('data-in/department-contacts.tsv', sep='\t', header = 0) \
    .rename(columns={'GitHub Username': 'dc_login', 'Department': 'name'}) \
    [['dc_login', 'name']] \
    .groupby('name', as_index=False) \
    .agg({'dc_login': ', '.join})

# df_departments; all memberships of a user with a department team
df_departments = (df_teams_members \
    .merge(df_department_contacts) \
    .rename(columns={'name': 'department'})
)[['login', 'department']]


# *** Construct df_admins
# df_collaborator_permissions; each row represents a user X having permissions for repo Y 
df_collaborators = pd.json_normalize(
    governance_json['repos'],
    'collaborators',
    ['full_name']
)
# df_admins; each row represents a user X that both:
# (a) has admin permissions for repo Y (admin == True)
# (a) is not an organization owner (owner != "admin" )
df_admins = (df_collaborators \
    .merge(df_associates) \
    .query('admin == True and role != "admin"') \
    .rename(columns={'full_name': 'repo'})
)[['login', 'repo']]

# *** Report
# Map repos to departments via admins
df_repos_departments = df_admins \
    .merge(df_departments, how = 'left') \
    .merge(df_associates, how = 'left') 

# Map outside collaborators to departments via df_collaborators
df_ocs_departments = df_ocs \
    .merge(df_collaborators) \
    .rename(columns={'full_name': 'repo'}) \
    .merge(
        df_repos_departments[df_repos_departments['department'].notna()][['repo', 'department']]
    ) \
   .agg({'login': 'unique'}) \
   .agg({'repo': ', '.join}) \

df_ocs_departments.to_csv('data-out/df_ocs_departments.csv', index = True)