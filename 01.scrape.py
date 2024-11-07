# 01.scrape.py
#
# Scrape a GitHub organization by collecting the metadata of the organization, each repo, and each commit to each repo.
# The output of this script is collected into org_out; a serializable representation of GitHub metaddata queried via the REST API. 
# The root node represents the organization, with elements in org_out['repos'] representing repos of the organization
# Each node has keys 'raw_data' and 'raw_headers' for the data and headers returned by GitHub for that node
# See https://pygithub.readthedocs.io/en/stable/github_objects.html?highlight=raw_data#github.GithubObject.GithubObject.raw_data
#
# Thomas Pronk, 2024-11-07

# Libraries
import os, json
from github import Github
from github import Auth

# Copying raw responses from PyGitHub to a dict
def dictify_response(source):
    return {
        'raw_data': source.raw_data,
        'raw_headers': source.raw_headers
    }

# Login to GitHub
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)

# org_out = {}

# Process the current organization
org_in = g.get_organization('AmsterdamUMC')
org_out = dictify_response(org_in)
org_out['repos'] = []
print(json.dumps(org_out, indent = 2))

# Process each repo of the current organization
for repo_in in org_in.get_repos():
    repo_out = dictify_response(repo_in)
    repo_out['commits'] = []
    print(json.dumps(repo_out, indent = 2))

    # Process each commit of the current repo
    try:
        for commit_in in repo_in.get_commits():
            commit_out = dictify_response(commit_in)
            print(json.dumps(commit_out, indent = 2))
            repo_out['commits'].append(commit_out)
    except Exception as e:
        repo_out['exception'] = e.data

    org_out['repos'].append(repo_out)

# Wrap up repodata
print(json.dumps(org_out, indent = 2))
with open('data-out/scraped_data.json', 'w') as f:
    json.dump(org_out, f)

# Close connections
g.close()


