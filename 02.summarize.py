# 02.summarize.py
#
# Summarize the scraped repos into tables

# 
import json, pandas as pd

tables = {}
with open('data-out/scraped_data.json') as f:
    scraped_data = json.load(f)

def flatten(response):
    return {**response['raw_data'], **response['raw_headers']}


flat_repos = []
flat_commits = []
summaries = []
for repo in scraped_data['repos']:
    summary = {}
    flat_repo = flatten(repo)
    flat_repos.append(flat_repo)
    summary['html_url'] = repo['raw_data']['html_url']
    for commit in repo['commits']:
        flat_commit = flatten(commit)
        flat_commit['repo.html_url'] = repo['raw_data']['html_url']
        try:
            flat_commit['author.login'] = commit['raw_data']['author']['login']
        except:
            pass

        try:
            flat_commit['author.name'] = commit['raw_data']['commit']['author']['name']
        except:
            pass

        flat_commits.append(flat_commit)

df_repos = pd.DataFrame(flat_repos)
df_commits = pd.DataFrame(flat_commits)

df_repos.to_csv('data-out/repos.csv', index=False)
df_commits.to_csv('data-out/commits.csv', index=False)