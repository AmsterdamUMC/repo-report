import os
from github import Github

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

gh = Github(GITHUB_TOKEN)

user = gh.get_user()
print(user.login)
