# 02.a.summarize_repos.py

import math, json, pandas as pd
pd.options.display.max_rows = 2000

# *** Summarize the governance data into a set of tables
with open('data-in/governance.clean.json') as f:
    governance_json = json.load(f)

# Repos
df_collaborators = pd.json_normalize(
    governance_json['repos'],
    'collaborators',
    ['full_name']
)
# Number of collaborators per repo
df_n_repo_user_total = df_collaborators \
    [['full_name', 'login']]. \
    groupby('full_name', as_index=False). \
    count(). \
    rename(columns={'login': 'user_total'})


df_n_repo_user_roles = df_collaborators \
    [['full_name', 'admin', 'maintain', 'push', 'triage', 'pull']]. \
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
df_repo_summary = df_n_repo_user_total. \
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

# Organization roles by users
df_organization_roles_users = pd.json_normalize(
    governance_json['organization_roles'],
    'users',
    ['name']    
)
#df_organization_roles_users.to_csv('data/governance.organization_roles_users.csv', index=False)

# *** Escalation paths: direct admins, department contact (dc), owner

# Escalation level 3. Organization owners
owners = df_members \
    .loc[df_members['role'] == 'admin']['login'] \
    .to_list()

# Escalation level 2. Department contact (associated with repo or repo admins)
# df_department_contacts has one row per department
df_department_contacts = pd \
    .read_csv('data-in/department-contacts.tsv', sep='\t', header = 0) \
    .rename(columns={'GitHub Username': 'dc_login', 'Department': 'name'}) \
    [['dc_login', 'name']] \
    .groupby('name', as_index=False) \
    .agg({'dc_login': ', '.join})

# Escalation level 1. A valid repo admins: a direct admin of a repo who is an organization member, 
# but not an organization owner
df_valid_repo_admins = df_members \
    .loc[df_members['role'] == 'member'] \
    .merge(df_collaborators.loc[df_collaborators['admin']]) \
    [['login', 'full_name']]

# Escalation level 2a. Department teams that the valid repo admins are a member of
df_joined_valid_repo_admin_departments = df_valid_repo_admins \
    .merge(df_teams_members) \
    .merge(df_department_contacts) \
    .groupby(['full_name'], as_index=False) \
    .count() \
    [['full_name']]

df_joined_valid_repo_admin_departments['departments'] =  df_valid_repo_admins \
    .merge(df_teams_members) \
    .merge(df_department_contacts) \
    .groupby(['full_name'], as_index=False) \
    .agg({'name': 'unique'}) \
    .agg({'name': ', '.join}) \
    .rename(columns={'name': 'departments'}) 

df_joined_valid_repo_admins = df_valid_repo_admins \
    .groupby('full_name', as_index=False) \
    .agg({'login': ', '.join}) \
    .rename(columns={'login': 'admins'}) 

# Add escalation paths to summary
df_repo_summary = df_repo_summary \
    .merge(df_joined_valid_repo_admins, how='left') \
    .merge(df_joined_valid_repo_admin_departments, how='left')

df_repo_summary.to_csv('data-out/repo_summary.csv', index=False)

# Make member summary
df_member_summary = df_department_contacts \
    .merge(df_teams_members, how='left') \
    .groupby(['login'], as_index=True) \
    .agg({'name': 'unique'}) \
    .agg({'name': ', '.join}) \
    .rename(columns={'name': 'departments'}) 

df_member_summary.to_csv('data-out/member_summary.csv', index = True)

# Report members that are not associated with any departments
df_members_summary = df_members \
    .merge(
        df_teams_members[df_teams_members['name'].isin(df_department_contacts['name'])][['login', 'name']],
        how = 'left',
        on = 'login'
    )
list(df_members_summary[df_members_summary['name'].isna()]['login'])

# Associate outside collaborators with departments via the private repos that they have permissions for

# Repo names and visibility levels
df_repos = pd.json_normalize(
    governance_json['repos'],
    meta = ['full_name', 'visibility']
)[['full_name', 'visibility']]

# Only private repos
df_repos_private = df_repos[df_repos['visibility'] == 'private']

# For each outide collaborator, list each private repo they have permissions for, and link those repos to departments
df_ocs_by_private_repos = df_repos_private \
    .merge(df_collaborators, how = 'left') \
    .merge(df_ocs, how = 'right') \
    .merge(df_repo_summary[['full_name', 'departments']], how = 'left')

# Export to table: list of outside collaborators and the private repos each has access to
df_ocs_by_private_repos.to_csv('data-out/outside_collaborator_summary.csv', index = True)

# Read audit log
audit_json = []
with open('data-in/audit_log.00.json', 'r') as f:
    for line in f:
        if line.strip():  # skip empty lines
            audit_json.append(json.loads(line))

# Get dates that members and outside collaborators got added to the organization
df_audit = pd.json_normalize(audit_json)
df_audit_member = df_audit[df_audit['action'].isin(['org.add_member'])]
df_audit_member = df_audit_member[['@timestamp', 'actor', 'action', 'user']]
df_audit_member = df_audit_member.rename(columns = {'user': 'subject', '@timestamp': 'timestamp'})

df_audit_oc = df_audit[df_audit['action'].isin(['org.add_outside_collaborator'])]
df_audit_oc = df_audit_oc[['@timestamp', 'actor', 'action', 'invitee']]
df_audit_oc = df_audit_oc.rename(columns = {'invitee': 'subject', '@timestamp': 'timestamp'})

df_audit_users = pd.concat([df_audit_member, df_audit_oc], ignore_index=True)
df_audit_users = df_audit_users.sort_values(by='timestamp')
df_audit_users['date_added'] = pd.to_datetime(df_audit_users['timestamp'], unit = 'ms')

# Offset: number of users at start of audit logs
offset = 44
df_audit_users['user_count'] = range(offset, len(df_audit_users) + offset)

# invitee
df_audit_users.to_csv('data-out/date_added.csv', index = True)
 
# Draw user counts
import matplotlib.pyplot as plt
import numpy as np
x = df_audit_users['date_added']
x2 = df_audit_users['timestamp']
y = df_audit_users['user_count']
plt.plot(x, y)
plt.xlabel('Time')
plt.ylabel('Count')
plt.title('Number of members & outside collaborators over the past year')
plt.xticks(rotation=45)
plt.tight_layout()
ax = plt.gca()
ax.set_ylim([0, len(df_audit_users) + offset])
z = np.polyfit(x2, y, 1)
p = np.poly1d(z)
plt.plot(x, p(x2), linestyle = '--')
plt.show()


