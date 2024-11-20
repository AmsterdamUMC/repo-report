# 01.b.scrape_histories.py
#
# Scrape the commit histories of each repo boling to a GitHub organization.
#
# Thomas Pronk, 2024-11-07

# *** Libraries
import os, json
from github import Github
from github import Auth
from shared import log_raw

# *** Constants
ORG_NAME = os.environ['ORG_NAME']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

# *** Globals
hist_out = []
raw_out = []

# *** Main

# Login to GitHub
auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)

# Process the current organization
org_in = gh.get_organization(ORG_NAME)
log_raw(raw_out, 'gh.get_organization(ORG_NAME)', org_in)

# Process each repo of the current organization
for repo_in in org_in.get_repos():
    log_raw(raw_out, 'org_in.get_repos()', repo_in)    
    repo_out = {
        'full_name': repo_in.full_name,
        'commits': []
    }    

    try:
        # Process each commit of the current repo
        for commit_in in repo_in.get_commits():
            log_raw(raw_out, 'repo_in.get_commits()', commit_in)

            # Commit SHA and parents
            commit_out = {
                'sha': commit_in.sha,
                'parents': []
            }

            # Add commit parents
            for parent_in in commit_in.parents:
                commit_out['parents'].append({
                    'sha': parent_in.sha
                })

            # Four ways to get a name or login for the commit via the GitHub REST API
            try:
                commit_out['login'] = commit_in.login
            except Exception as e:
                commit_out['login'] = None

            try:
                commit_out['author_login'] = commit_in.author.login
            except Exception as e:
                commit_out['author_login'] = None

            try:
                commit_out['commit_author_name'] = commit_in.commit.author.name
            except Exception as e:
                commit_out['commit_author_name'] = None

            try:
                commit_out['commit_committer_name'] = commit_in.commit.committer.name
            except Exception as e:
                commit_out['commit_committer_name'] = None

            repo_out['commits'].append(commit_out)
    except Exception as e:
        repo_out['error'] = str(e)
    hist_out.append(repo_out)

# Wrap up repodata
print(json.dumps(hist_out, indent = 2))
with open('data/provenance.clean.json', 'w') as f:
    json.dump(hist_out, f, indent = 2)
with open('data/provenance.raw.json', 'w') as f:
    json.dump(raw_out, f, indent = 2)

# Close connections
gh.close()


