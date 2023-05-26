import pandas as pd
import requests
import json

# Fake tokens. Generate your own and replace these
token_list = ["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"]
# Sample repository. Replace it with your own repository
reponame = "CivBuilder/Carbon"
ct = 0
# Date to start collecting data from
ignore_date = pd.to_datetime("2023-03-28T00:00:00-00:00", utc=True)
# File extensions to ignore from the graphs
ignored_file_extensions = [
    ".pdf",
    ".xml",
    ".html",
    ".css",
    ".log",
    ".txt",
    ".json",
]

"""
@url Github API URL for extracting the
@token_list a list of GitHub tokens
@ct token counter
"""

"""
@url Github API URL for extracting the
@token_list a list of GitHub tokens
@ct token counter
"""


def get_response(url, token_list, ct):
    jsonData = None

    len_tokens = len(token_list)
    try:
        ct = ct % len_tokens
        headers = {"Authorization": "Token {}".format(token_list[ct])}
        request = requests.get(url, headers=headers)
        jsonData = json.loads(request.content)
        ct += 1
    except Exception as e:
        ct += 1
        print(e)
    return jsonData, ct

# This function returns the a list of contributor's names and login-names

def contributors(reponame, token_list, ct):
    contributor_names = []
    contributor_logins = []
    login_to_name = dict()

    api = "https://api.github.com/repos/" + reponame + "/contributors"

    try:
        contributor_array, ct = get_response(api, token_list, ct)

        if contributor_array is not None:
            for contributor_obj in contributor_array:
                contributor_name = ""
                contributor_api = "https://api.github.com/users/" + contributor_obj["login"]
                contributor_obj2, ct = get_response(contributor_api, token_list, ct)
                if contributor_obj2 is not None:
                    # Exclude all the contributors with name = null in the GitHub User API
                    if contributor_obj2["name"] is not None:
                        contributor_name = contributor_obj2["name"].split(" ")[0]
                        login_to_name[contributor_obj["login"]] = contributor_name

    except Exception as e:
        print(e)
    return login_to_name, ct


login_to_name, ct = contributors(reponame, token_list, ct)
print(login_to_name)

# This function takes in the contributor list returned in the
# previous cell


def pullrequest_details(reponame, login_to_name, token_list, ct):
    contributor_pr_count = dict()
    contributor_pr_review_count = dict()
    contributor_changedFiles_count = dict()
    contributor_changedLOC = dict()

    try:
        # loop though all the commit pages until the last returned empty page
        ipage = 1
        while True:
            spage = str(ipage)
            pr_api = "https://api.github.com/repos/" + reponame + "/pulls?page=" + spage + "&per_page=100&state=closed"
            pr_list, ct = get_response(pr_api, token_list, ct)

            # break out of the while loop if there are no more commits in the pages
            if len(pr_list) == 0:
                break

            # iterate through the list of pull requests in page
            for pr_obj in pr_list:
                pr_number = pr_obj["number"]
                login = pr_obj["user"]["login"]
                contri_name = login_to_name[login]

                # Only count PRs that were merged
                if pr_obj["merged_at"] is not None:
                    merged_at = pr_obj["merged_at"]

                    date1 = pd.to_datetime(merged_at, utc=True)
                    difference = date1 - ignore_date
                    difference = difference.total_seconds() // 3600

                    # Only count PRs that were merged after the ignore_date
                    if difference > 0:

                        # Increase contributor's PR count
                        contributor_pr_count[contri_name] = contributor_pr_count.get(contri_name, 0) + 1

                        # Print the title of the PR (for debugging)
                        # print(pr_obj['title'])

                        """
                            We want to identify the authors of each chached file in the PR. First, we 
                            shall collect a list of PR-files and list of PR-commits. Second, we iterate
                            through a list of commits and pick the files changed in each commit and identify
                            the commit author as well as the files they changed. Lastly, we compare the files 
                            in the commits and those in PR-files and assign them to the different authors. 
                            """

                        # we only care about changed files in a PR, not the individual commits
                        pr_changedFiles_api = "https://api.github.com/repos/" + reponame + "/pulls/" + str(pr_number) + "/files"
                        pr_changedFiles_list, ct = get_response(pr_changedFiles_api, token_list, ct)

                        # Add the number of changed files to the contributor's count and lines of code changed
                        for file_obj1 in pr_changedFiles_list:
                            file = file_obj1["filename"]

                            # if file does not end with any of the ignored file extensions (declared above),
                            # add it to the LOC count & changed files count
                            if not any(file.endswith(x) for x in ignored_file_extensions):

                                # A note about the changed files, it does not track unique files,
                                # but rather the number of files changed in a PR irregardless if they already changed them before or not.
                                contributor_changedFiles_count[contri_name] = contributor_changedFiles_count.get(contri_name, 0) + 1

                                contributor_changedLOC[contri_name] = contributor_changedLOC.get(contri_name, 0) + file_obj1["changes"]

                                # Optional print statement to see the files and LOC changed by each contributor
                                # print(contri_name + " " + str(file) + " " + str(file_obj1['changes']) + " " + str( contributor_changedLOC.get(contri_name, 0)))

                        pr_reviews_api = "https://api.github.com/repos/" + reponame + "/pulls/" + str(pr_number) + "/reviews?per_page=100"

                        pr_reviews_list, ct = get_response(pr_reviews_api, token_list, ct)

                        # Check if we have already counted a reviewer
                        # This is to ensure that people that just commented on a PR receive proper credit
                        # Even if they have not approved the PR.
                        already_reviewed = set()
                        if len(pr_reviews_list) != 0:
                            for pr_review_obj in pr_reviews_list:
                                login = pr_review_obj["user"]["login"]
                                # Ignore someone commenting that isnt apart of our group
                                if login not in login_to_name.keys():
                                    continue
                                reviewer_name = login_to_name[login]
                                if reviewer_name is not contri_name and reviewer_name not in already_reviewed:
                                    already_reviewed.add(reviewer_name)
                                    # print("Reviewed By: " + reviewer_name)
                                    contributor_pr_review_count[reviewer_name] = contributor_pr_review_count.get(reviewer_name, 0) + 1

            ipage += 1
    except Exception as e:
        print("Error receiving data")
        print(e)

    return (
        contributor_pr_count,
        contributor_pr_review_count,
        contributor_changedFiles_count,
        contributor_changedLOC,
        ct,
    )


(
    contributor_pr_count,
    contributor_pr_review_count,
    contributor_changedFiles_count,
    contributor_changedLOC,
    ct,
) = pullrequest_details(reponame, login_to_name, token_list, ct)

print("contributor_pr_count", contributor_pr_count)
print("contributor_pr_review_count", contributor_pr_review_count)
print("contributor_changedFiles_count", contributor_changedFiles_count)
print("contributor_changedLOC", contributor_changedLOC)

# This function processes the issue details of a repository
def issue_details(reponame, login_to_name, token_list, ct):
    contributor_issue_count = dict()
    contributor_comment_count = dict()

    try:
        # loop though all the commit pages until the last returned empty page
        ipage = 1
        while True:
            spage = str(ipage)
            issue_api = "https://api.github.com/repos/" + reponame + "/issues?page=" + spage + "&per_page=100&state=all"
            issue_array, ct = get_response(issue_api, token_list, ct)

            # break out of the while loop if there are no more commits in the pages
            if len(issue_array) == 0:
                # print("no issues", issue_api)
                break

            # iterate through the list of issues and colloect the issue contributors
            for issue_obj in issue_array:

                date1 = pd.to_datetime(issue_obj["created_at"], utc=True)
                difference = date1 - ignore_date
                difference = difference.total_seconds() // 3600

                if "pull_request" not in issue_obj.keys() and difference > 0:

                    login = issue_obj["user"]["login"]
                    contri_name = login_to_name[login]

                    # Original creator of the issue
                    contributor_issue_count[contri_name] = contributor_issue_count.get(contri_name, 0) + 1

                    # Add the number of comments to the collection array
                    issue_comments_api = issue_obj["comments_url"]
                    issue_comment_array, ct = get_response(issue_comments_api, token_list, ct)
                    if len(issue_comment_array) != 0:
                        for issue_comment_obj in issue_comment_array:
                            commenter_login = issue_comment_obj["user"]["login"]
                            commentor_name = login_to_name[commenter_login]
                            contributor_comment_count[commentor_name] = contributor_comment_count.get(commentor_name, 0) + 1

            ipage += 1
    except Exception as e:
        print(e)
        print("Error receiving data")

    return contributor_issue_count, contributor_comment_count, ct


contributor_issue_count, contributor_comment_count, ct = issue_details(reponame, login_to_name, token_list, ct)

print("contributor_issue_count", contributor_issue_count)
print("contributor_comment_count", contributor_comment_count)

df_pr = pd.DataFrame(contributor_pr_count.items(), columns=["Login", "PRs"])
df_prReviews = pd.DataFrame(contributor_pr_review_count.items(), columns=["Login", "PR_Reviews"])
df_pr_ChangedFiles = pd.DataFrame(contributor_changedFiles_count.items(), columns=["Login", "Changed_Files"])
df_pr_ChangedLOC = pd.DataFrame(contributor_changedLOC.items(), columns=["Login", "Changed_LOC"])
df_issues = pd.DataFrame(contributor_issue_count.items(), columns=["Login", "Issues"])
df_issues_comments = pd.DataFrame(contributor_comment_count.items(), columns=["Login", "Issue_Comments"])

from functools import reduce

df_list = [
    df_pr,
    df_prReviews,
    df_issues,
    df_issues_comments,
    df_pr_ChangedFiles,
    df_pr_ChangedLOC,
]
df_merged = reduce(lambda left, right: pd.merge(left, right, on=["Login"], how="outer"), df_list)
df_merged = df_merged.fillna(0).sort_values("Changed_LOC", ascending=[0])
df_merged = df_merged.head(25)
df_merged.sort_index(inplace=True)
df_merged = df_merged.head(13)

# Replace the login names with your real names in the report

import matplotlib.pyplot as plt

fig = plt.figure()

plt.style.use("classic")
ax = df_merged.plot(x="Login", y=["PRs", "PR_Reviews", "Issues", "Issue_Comments"], kind="bar", rot=45)
plt.tight_layout()
plt.show()
# plt.savefig('../img/contributions.pdf')

plt.style.use("classic")
ax = df_merged.plot(x="Login", y=["Changed_Files"], kind="bar", rot=45)
plt.tight_layout()
plt.show()

fig = plt.figure()

plt.style.use("classic")
ax = df_merged.plot(x="Login", y=["Changed_LOC"], kind="bar", rot=45)
plt.tight_layout()
plt.show()

