# utils/jira_utils.py  
  
import os  
import logging  
from jira import JIRA, JIRAError  
from dotenv import load_dotenv  
import pprint
  
# Load environment variables from .env file  
load_dotenv()  
  
# Set the JIRA credentials and server  
jira_server = os.getenv('2023sept8_JIRA_SERVER')  

print("printing out the jira server proving we have value...  ")
print(jira_server)


jira_server_env = os.environ.get("APPSETTING_2023sept8_JIRA_SERVER", "cannot find the jira server")
print("printing out the jira server from env variable proving we have value...  ")
print(jira_server_env)

print(os.environ)



username = os.getenv('APPSETTING_2023sept8_JIRA_USERNAME')  
api_token = os.getenv('APPSETTING_2023sept8_JIRA_TOKEN')  
parent_key = os.getenv('APPSETTING_2023sept8_JIRA_PARENT_KEY')  
project_name = os.getenv('APPSETTING_2023sept8_JIRA_PROJECT_NAME')  
default_account_id = os.getenv('APPSETTING_2023oct6_JIRA_DEFAULT_USER_ACCOUNT_ID')  
default_label_title = os.getenv('APPSETTING_2023oct6_JIRA_DEFAULT_LABEL_TITLE')  
  
# Connect to JIRA Server  
jira = JIRA(server=jira_server, basic_auth=(username, api_token))  
  
async def fetch_issue_details(issue_key):  
    try:  
        issue = jira.issue(issue_key)  
  
        # Pretty-print the raw JIRA issue data  
        logging.debug("Raw JIRA issue data:")  
        pprint.pprint(issue.raw)  
  
        # Fetch comments  
        comments = [  
            {  
                "author": comment.author.displayName,  
                "body": comment.body,  
                "created": comment.created  
            }  
            for comment in issue.fields.comment.comments  
        ]  
  
        # Fetch child issues (subtasks or issues linked to an Epic)  
        child_issues = []  
        if issue.fields.issuetype.name.lower() == 'epic':  
            jql = f'"Epic Link" = {issue_key}'  
            child_issues_result = jira.search_issues(jql)  
            child_issues = [  
                {  
                    "key": child.key,  
                    "summary": child.fields.summary  
                }  
                for child in child_issues_result  
            ]  
        else:  
            child_issues = [  
                {  
                    "key": subtask.key,  
                    "summary": subtask.fields.summary  
                }  
                for subtask in issue.fields.subtasks  
            ]  
  
        return {  
            "key": issue.key,  
            "summary": issue.fields.summary,  
            "description": issue.fields.description,  
            "status": issue.fields.status.name,  
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",  
            "reporter": issue.fields.reporter.displayName,  
            "priority": issue.fields.priority.name if issue.fields.priority else "No Priority",  
            "created": issue.fields.created,  
            "updated": issue.fields.updated,  
            "resolutiondate": issue.fields.resolutiondate,  
            "labels": issue.fields.labels,  
            "components": [component.name for component in issue.fields.components],  
            "issuetype": issue.fields.issuetype.name,  
            "project": issue.fields.project.key,  
            "votes": issue.fields.votes.votes if issue.fields.votes else 0,  
            "comments": comments,  
            "child_issues": child_issues  
        }  
    except JIRAError as e:  
        if e.status_code == 404:  
            logging.error(f"Issue {issue_key} not found in JIRA.")  
            return None  
        else:  
            logging.error(f"Error fetching issue details: {e}")  
            raise  

