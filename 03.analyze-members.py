# 02.a.analyze_members.py
# Produces a table of members, with metadata on whether the member is registered in our
# administration, and when/who onboarded them

# Libraries & global settings
import math, json, pandas as pd
pd.options.display.max_rows = 2000

# *** Table of current members, obtained via REST API

# Some minmal processing; only to convert the JSON array of members to a pandas data 

# Read governance.clean.json
with open('data/github-snapshot.json') as f:
    governance_json = json.load(f)

# Convert the JSON array of members to a pandas data frame
df_members = pd.json_normalize(
    governance_json['members']
)

# *** Table of events in audit log where a member got added to the organization, obtained via GUI

# We conduct a series of operations to get a table that can easily be joined with
# df_members. It contains a shared column "login" for joining the tables together and a
# "history" column with a human readable summary of who added the member when.
# For example, "2024-05-01. alice. Added member to organization"

# Read audit log into a data frame
df_audit = pd.read_csv('data/audit-log.tsv', sep="\t", low_memory=False)

# Find audit log entries where a member got added to the organization
df_audit_member_added = df_audit[df_audit['action'].isin(['org.add_member'])]

# Select relevant columns
df_audit_member_added = df_audit_member_added[['@timestamp', 'actor', 'user']]

# Rename columns for clarity & to align with df_members
df_audit_member_added = df_audit_member_added.rename(columns = {'user': 'login', '@timestamp': 'timestamp'})

# Convert the timestamp to an ISO standard for readability (date only)
df_audit_member_added['timestamp'] = pd.to_datetime(df_audit_member_added['timestamp'], unit = 'ms').dt.date

# Create a column with formatted message
df_audit_member_added['history_audit'] = \
    df_audit_member_added['timestamp'].astype(str) + '. ' + \
    df_audit_member_added['actor'] + '. Added member to organization'

# Select relevant columns
df_audit_member_added = df_audit_member_added[['login', 'history_audit']]

# *** Table of Member Contact Information

# Table of member contact information, obtained from our administration.
# We'll outer join this table with df_members to get a table with the logins present in both tables.

# Read member contact information from data/member_contacts.tsv
df_member_ci = pd.read_csv('data/member-contact-information.tsv', sep='\t')

# Rename "history" to "history_ci" to distinguish it from the audit log history
df_member_ci = df_member_ci.rename(columns = {'history': 'history_ci'})


# *** Join the tables together

# Join df_members with audit history (left join; only add audit history for current members))
df_members = df_members.merge(df_audit_member_added, how='left', on='login')

# Join df_members with df_members_ci (outer; we want to keep all members from both)
df_joined = df_member_ci.merge(df_members, how='outer', on='login')

# Merge the history columns together, to have a single column with all history information (from both audit log and contact information)
# Multiple events in this history column are separated by "; ". For example, 
# "2024-05-01. alice. Added member to organization; 2024-06-01. bob. Updated contact information"
def merge_history(row):
    history_items = [str(row['history_audit']) if pd.notna(row['history_audit']) else '', 
                     str(row['history_ci']) if pd.notna(row['history_ci']) else '']
    return '; '.join(filter(None, history_items))

df_joined['history'] = df_joined.apply(merge_history, axis=1)

# Drop the original history columns, as we now have a single merged history column
df_joined = df_joined.drop(columns=['history_audit', 'history_ci'])

# Write the joined table to a TSV
df_joined.to_csv('data/members-joined.tsv', sep='\t', index=False)