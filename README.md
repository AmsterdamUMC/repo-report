# repo-report
Generate machine-actionable reports from the information contained in a GitHub organization.

# Requirements
Developed using Python 3.13.0

# How to install
1. Clone this repo to your device
2. Install the libraries in `requirements.txt`
3. Set up the two environment variables below:
    a. `GITHUB_TOKEN` containing a GitHub personal access token. It should provide the (classic) permissions `repo` and `admin:org`
    b. `ORG_NAME` containing the organization name

# How to use

## Produce a snapshot of the governance structure
Run `01.a.scrape_governance.py`. This script produces two output files:
* `data-out/governance.clean.json`, which contains the organization snapshot. See details of this file below.
* `data-out/governance.raw.json`, which contains raw headers and data for each request made by the script to the GitHUB REST API.

## Produce a snapshot of the provenance of the repositories
Run `01.b.scrape_provenance.py`. This script produces two output files:
* `data-out/provenance.clean.json`, which contains the provenance snapshot. I haven't documented this file yet.
* `data-out/provenance.raw.json`, which contains raw headers and data for each request made by the script to the GitHUB REST API.

## Details of `data-out/governance.raw.json`
This file is a JSON data structure containing a snapshot of the governance of the GitHub organization. Below is a summary of the information you can find in here, using [JSONPath](https://en.wikipedia.org/wiki/JSONPath) syntax to point to different parts of the file.

* `$.repos[*]` lists each repository of the organization. See the API documentation at [List organization repositories](https://docs.github.com/en/rest/repos/repos#list-organization-repositories)
    * `$.repos[*].full_name` identifies this repo by its name (`<login/organization>/<repo>`)
    * `$.repos[*].collaborators` lists each collaborator for this repo. See the API documentation at [List repository collaborators](https://docs.github.com/en/rest/collaborators/collaborators?apiVersion=2022-11-28#list-repository-collaborators) and a guide at [Repository roles for an organization](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)
        * `$.repos[*].collaborators[*].login` identifies this collaborator by their GitHub login name
        * `$.repos[*].collaborators[*].admin` corresponds to repository role **Admin**
        * `$.repos[*].collaborators[*].maintain` corresponds to repository role **Maintain**
        * `$.repos[*].collaborators[*].push` corresponds to repository role **Write**
        * `$.repos[*].collaborators[*].triage` corresponds to repository role **Triage**
        * `$.repos[*].collaborators[*].pull` corresponds to repository role **Read**
* `$.members` Each member of the organization. See the API documentation at [List organization members](https://docs.github.com/en/rest/orgs/members?apiVersion=2022-11-28#list-organization-members) and a guide at [Managing membership in your organization](https://docs.github.com/en/organizations/managing-membership-in-your-organization)
    *  `$.members[*].login` identifies this member via their GitHub login name
    * `$.members[*].role` identifies their role in relation to organization resources. For instance, normal members have the role `member` and organization owners `admin`. See the API documentation at [Get organization membership for a user](https://docs.github.com/en/rest/orgs/members#get-organization-membership-for-a-user) and a guide at [Roles in an organization](https://docs.github.com/en/organizations/managing-peoples-access-to-your-organization-with-roles/roles-in-an-organization)
    *  `$.members[*].state` identifies whether user is a full-fledged member (`active`) or not (any other value, such as `pending`?). I have not managed to have a user listed as anything else than non-active, neither after (1) removing a member from the organization, (2) inviting a user to become a member (without the invite being accepted yet), (3) same as 2 but for an outside collaborator.
* `$.outside_collaborators` Each outside collaborator of the organization. See the API documentation at [List outside collaborators for an organization](https://docs.github.com/en/rest/orgs/outside-collaborators#list-outside-collaborators-for-an-organization) and a guide at [Managing outside collaborators](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-outside-collaborators). To find the particular repos that an outside collaborator is collaborator of, look for (private) the repos listed under the outside collaborator or see the repos where `$.repos[*].collaborators[*].login` matches a collaborator login.
    *  `$.outside_collaborators[*].login` identifies this outside collaborator via their GitHub login name
* `$.teams` Each team of the organization. See the API documentation at [List teams](https://docs.github.com/en/rest/teams/teams#list-teams) and a guide at [About teams](https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams)
    *  `$.teams[*].id` identifies this team by its ID
    *  `$.teams[*].name` identifies this team by its name
    *  `$.teams[*].parent` identifies this team's parent, if any
        *  `$.teams[*].parent.id` identifies this team's parent by its ID
        *  `$.teams[*].parent.name` identifies this team's parent by its name
    *  `$.teams[*].members` lists this team's members
        *  `$.teams[*].members[*].login` identifies this team member via their GitHub login name
        *  `$.teams[*].members[*].role` the team member role, being a standard member (`member`) or a team maintainer (`maintainer`). See a guide at [Assigning the team maintainer role to a team member](https://docs.github.com/en/organizations/organizing-members-into-teams/assigning-the-team-maintainer-role-to-a-team-member)
        *  `$.teams[*].members[*].state` identifies whether user is a full-fledged member (`active`) or not (any other value, such as `pending`?). See `$.members[*].state`
    *  `$.teams[*].repos` lists this team's repos. See a guide at [Repository roles for an organization](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)
        * `$.teams[*].repos[*].full_name`  identifies this repo by its name (`<login/organization>/<repo>`)
        * `$.teams[*].repos[*].admin` corresponds to repository role **Admin**
        * `$.teams[*].repos[*].maintain` corresponds to repository role **Maintain**
        * `$.teams[*].repos[*].push` corresponds to repository role **Write**
        * `$.teams[*].repos[*].triage` corresponds to repository role **Triage**
        * `$.teams[*].repos[*].pull` corresponds to repository role **Read**
* `$.organization_roles` Each custom organization role. See the API documentation at [Get all organization roles for an organization](https://docs.github.com/en/rest/orgs/organization-roles#get-all-organization-roles-for-an-organization) and a guide at [About pre-defined organization roles](https://docs.github.com/en/organizations/managing-peoples-access-to-your-organization-with-roles/roles-in-an-organization#about-pre-defined-organization-roles)
    * `$.organization_roles[*].id` identifies this organization role via its ID
    * `$.organization_roles[*].name` is the name of this organization role
        * `all_repo_read` corresponds to **All-repository read**: Grants read access to all repositories in the organization.
        * `all_repo_write` corresponds to **All-repository write**: Grants write access to all repositories in the organization.
        * `all_repo_triage` corresponds to **All-repository triage**: Grants triage access to all repositories in the organization.
        * `all_repo_maintain` corresponds to **All-repository maintain**: Grants maintenance access to all repositories in the organization.
        * `all_repo_admin` corresponds to **All-repository admin**: Grants admin access to all repositories in the organization.
        * `ci_cd_admin` corresponds to **CI/CD admin**: Grants admin access to manage Actions policies, runners, runner groups, hosted compute network configurations, secrets, variables, and usage metrics for an organization.
    * `$.organization_roles[*].teams` lists teams that have this organization role
        *  `$.organization_roles[*].teams[*].id` identifies this team by its ID
        *  `$.organization_roles[*].teams[*].name` identifies this team by its name
    * `$.organization_roles[*].users` lists users that have this organization role
        *  `$.organization_roles[*].users[*].id` identifies this user by its ID
        *  `$.organization_roles[*].users[*].login` identifies this user by its login
