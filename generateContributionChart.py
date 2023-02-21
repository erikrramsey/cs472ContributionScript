
import pandas as pd
import requests
import json
from functools import reduce

'''
@url Github API URL for extracting the
@token_list a list of GitHub tokens
@ct token counter
'''
token_list = ['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']

def get_response(url, token_list, ct):
    jsonData = None

    len_tokens = len(token_list)
    try:
        ct = ct % len_tokens
        headers = {'Authorization': 'Bearer {}'.format(token_list[ct])}
        request = requests.get(url, headers=headers)
        jsonData = json.loads(request.content)
        ct += 1
    except Exception as e:
        ct += 1
        print(e)
    return jsonData, ct

# Sample repository. Replace it with your own repository
reponame = 'CivBuilder/cs472project'
contribution = ['PR', 'PR-reviews', 'changedFileCount', 'changedLOC', 'Issues', 'Issue-comments']
ct = 0

# This function returns the a list of contributor's names and login-names
def contributors(reponame, token_list, ct):
    contributor_names = []
    contributor_logins = []

    api = 'https://api.github.com/repos/' + reponame + '/contributors'

    try:
        contributor_array, ct = get_response(api, token_list, ct)

        if contributor_array is not None:
            for contributor_obj in contributor_array:
                contributor_name = ''
                contributor_logins.append(contributor_obj['login'])
                contributor_api = 'https://api.github.com/users/' + contributor_obj['login']
                contributor_obj2, ct = get_response(contributor_api, token_list, ct)
                if contributor_obj2 is not None:
                    contributor_name = contributor_obj2['name']
                contributor_names.append(contributor_name)

    except Exception as e:
        print(e)
    # print(contributor_logins)
    return contributor_names, contributor_logins, ct

contributor_names, contributor_logins, ct = contributors(reponame, token_list, ct)
print('Number of Repository contributors', len(contributor_logins))



# This function takes in the contributor list returned in the
# previous cell

def pullrequest_details(reponame, contributor_logins, token_list, ct):
    contributor_pr_count = dict()
    contributor_changedFiles_count = dict()
    contributor_changedLOC = dict()
    contributor_pr_review_count = dict()

    try:
        # loop though all the commit pages until the last returned empty page
        ipage = 1
        while True:
            spage = str(ipage)
            pr_api = 'https://api.github.com/repos/' + reponame + '/pulls?page=' + spage + \
                     '&per_page=100&state=closed'
            pr_list, ct = get_response(pr_api, token_list, ct)

            # break out of the while loop if there are no more commits in the pages
            if len(pr_list) == 0:
                break
            for contri_login in contributor_logins:
                # iterate through the list of pull requests in  spage
                for pr_obj in pr_list:
                    pr_number = pr_obj['number']
                    login = pr_obj['user']['login']
                    if login is not None:
                            if contri_login == login:
                                contributor_pr_count[login] = contributor_pr_count.get(login, 0) + 1
                                pr_reviews_api = 'https://api.github.com/repos/' + reponame + '/pulls/' \
                                                 + str(pr_number) + '/reviews'
                                pr_reviews_list, ct = get_response(pr_reviews_api, token_list, ct)
                                if len(pr_reviews_list) != 0:
                                    for pr_review_obj in pr_reviews_list:
                                        reviewer_login = pr_review_obj['user']['login']
                                        if contri_login == reviewer_login:
                                            contributor_pr_review_count[login] = contributor_pr_count.\
                                                                                     get(login, 0) + 1
                                '''
                                We want to identify the authors of each chached file in the PR. First, we 
                                shall collect a list of PR-files and list of PR-commits. Second, we iterate
                                through a list of commits and pick the files changed in each commit and identify
                                the commit author as well as the files they changed. Lastly, we compare the files 
                                in the commits and those in PR-files and assign them to the different authors. 
                                '''
                                pr_changedFiles_api = 'https://api.github.com/repos/' + reponame + '/pulls/' \
                                                 + str(pr_number) + '/files'
                                pr_changedFiles_list, ct = get_response(pr_changedFiles_api, token_list, ct)
                                
                                pr_commits_api = 'https://api.github.com/repos/' + reponame + '/pulls/' \
                                                 + str(pr_number) + '/commits'
                                pr_commit_list, ct = get_response(pr_commits_api, token_list, ct)
                                
                                for commit_obj in pr_commit_list:
                                    if commit_obj['committer']['login'] is not None:
                                        commit_login = commit_obj['committer']['login']
                                        sha = commit_obj['sha']
                                        commit_sha_api = 'https://api.github.com/repos/' + reponame + '/commits/' + sha
                                        commit_file_obj, ct = get_response(commit_sha_api, token_list, ct)
                                        # exclude the merge commits (commits with more than one parent)
                                        if len(commit_file_obj['parents']) == 1:
                                            file_list = commit_file_obj['files']
                                            for com_file_obj in file_list:
                                                file = com_file_obj['filename']
                                                for file_obj1 in pr_changedFiles_list:
                                                    if file == file_obj1['filename'] and not file.endswith('.pdf') and not file.endswith('.xml') \
                                                                and not file.endswith('.html')  and not file.endswith('.css') and not file.endswith('.log') \
                                                                and not file.endswith('.txt'):
                                                        contributor_changedFiles_count[login] = contributor_changedFiles_count.get(login, 0) + 1
                                                        contributor_changedLOC[login] = contributor_changedLOC.get(login, 0) + file_obj1['changes']
                                                        break
                                                    
                                    
            ipage += 1
    except:
        print("Error receiving data")
        exit(0)

    return contributor_pr_count, contributor_pr_review_count,\
           contributor_changedFiles_count, contributor_changedLOC, ct

contributor_pr_count, contributor_pr_review_count,\
           contributor_changedFiles_count, contributor_changedLOC, ct = \
    pullrequest_details(reponame, contributor_logins, token_list, ct)

# This function processes the issue details of a repository
def issue_details(reponame, contributor_logins, token_list, ct):
    contributor_issue_count = dict()
    contributor_comment_count = dict()

    try:
        # loop though all the commit pages until the last returned empty page
        ipage = 0
        while True:
            spage = str(ipage)
            issue_api = 'https://api.github.com/repos/' + reponame + '/issues?state=all&' \
                                                                     'per_page=100&page=' + spage

            issue_array, ct = get_response(issue_api, token_list, ct)

            # break out of the while loop if there are no more commits in the pages
            if len(issue_array) == 0:
                break
            # iterate through the list of pull requests in  spage
            for contri_login in contributor_logins:
                for issue_obj in issue_array:
                    issue_number = issue_obj['number']
                    login = issue_obj['user']['login']
                    if login is not None:
                            if contri_login == login:
                                contributor_issue_count[login] = contributor_issue_count.get(login, 0) + 1
                                issue_comments_api = 'https://api.github.com/repos/' + reponame + '/issues/' \
                                                 + str(issue_number) + '/comments'
                                issue_comment_array, ct = get_response(issue_comments_api, token_list, ct)
                                if len(issue_comment_array) != 0:
                                    for issue_comment_obj in issue_comment_array:
                                        commenter_login = issue_comment_obj['user']['login']
                                        if contri_login == commenter_login:
                                            contributor_comment_count[login] = contributor_comment_count.\
                                                                                     get(login, 0) + 1

            ipage += 1
    except:
        print("Error receiving data")

    return contributor_issue_count, contributor_comment_count, ct
contributor_issue_count, contributor_comment_count, ct = \
    issue_details(reponame, contributor_logins, token_list, ct)



df_pr = pd.DataFrame(contributor_pr_count.items(), columns = ['Login','PRs'])
df_prReviews = pd.DataFrame(contributor_pr_review_count.items(), columns = ['Login','PR-Reviews'])
df_pr_ChangedFiles = pd.DataFrame(contributor_changedFiles_count.items(), columns = ['Login','ChangedFiles'])
df_pr_ChangedLOC = pd.DataFrame(contributor_changedLOC.items(), columns = ['Login','ChangedLOC'])
df_issues = pd.DataFrame(contributor_issue_count.items(), columns = ['Login','Issues'])
df_issues_comments = pd.DataFrame(contributor_comment_count.items(), columns = ['Login','Issues_comments'])




df_list = [df_pr, df_prReviews, df_issues, df_issues_comments, df_pr_ChangedFiles,df_pr_ChangedLOC]
df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['Login'],
                                            how='outer'), df_list)
df_merged = df_merged.fillna(0).sort_values('ChangedLOC', ascending=[0])
df_merged = df_merged.head(25)
df_merged.sort_index(inplace=True)
df_merged = df_merged.head(10)



# Replace the login names with your real names in the report
names = {
    'CivBuilder' : 'Chris Catechis',
    'erickserr125' : 'Erick Serrano',
    'aq6476' : 'Angel Quintanilla',
    'SnellJ2' : 'Jonas Snell',
    'JaneenSudiacal' : 'Janeen Sudiacal',
    'akummi' : 'Avery Nguyen',
    'adamantisaurus' : 'Adam Velardi',
    'mcebaniqued' : 'Miguel Baniqued',
    'erikrramsey' : 'Erik Ramsey',
    'dpw97' : 'David Weaver',
}

for i in range(0, df_merged.Login.size):
    df_merged.Login[i] = names[df_merged.Login[i]]

import matplotlib.pyplot as plt
fig = plt.figure()

plt.style.use('classic')
ax = df_merged.plot(x="Login", y=["PRs", "PR-Reviews", "Issues", "Issues_comments"], kind="bar", rot=45)

plt.tight_layout()
plt.show()

plt.style.use('classic')
ax = df_merged.plot(x="Login", y=["ChangedFiles"], kind="bar", rot=45)
plt.tight_layout()
plt.show()

fig = plt.figure()

plt.style.use('classic')
ax = df_merged.plot(x="Login", y=["ChangedLOC"], kind="bar", rot=45)
plt.tight_layout()
plt.show()

input()

# plt.savefig('../img/contributions.pdf')

