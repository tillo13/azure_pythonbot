# utils/jira_utils.py  
import os  
import logging  
from jira import JIRA, JIRAError  
from dotenv import load_dotenv  
  
# Load environment variables from .env file  
load_dotenv()  
  
jira_server = os.environ.get("APPSETTING_2023sept8_JIRA_SERVER")  
username = os.environ.get('APPSETTING_2023sept8_JIRA_USERNAME')  
api_token = os.environ.get('APPSETTING_2023sept8_JIRA_TOKEN')  
parent_key = os.environ.get('APPSETTING_2023sept8_JIRA_PARENT_KEY')  
project_name = os.environ.get('APPSETTING_2023sept8_JIRA_PROJECT_NAME')  
default_account_id = os.environ.get('APPSETTING_2023oct6_JIRA_DEFAULT_USER_ACCOUNT_ID')  
default_label_title = os.environ.get('APPSETTING_2023oct6_JIRA_DEFAULT_LABEL_TITLE')  
  
# Connect to JIRA Server  
jira = JIRA(server=jira_server, basic_auth=(username, api_token))  
  
async def fetch_issue_details(issue_key):  
    try:  
        issue = jira.issue(issue_key)  
        logging.debug("Raw JIRA issue data received... (debug by #uncommenting in jira_utils.py)")  
  
        comments = [  
            {  
                "author": comment.author.displayName,  
                "body": comment.body,  
                "created": comment.created  
            }  
            for comment in issue.fields.comment.comments  
        ]  
  
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
  
async def create_jira_task(subject, context):  
    try:  
        user_name = getattr(context.activity.from_property, 'name', None) or getattr(context.activity.from_property, 'id', 'Unknown')  
        description_text = (  
            f"Created by: {user_name}\n"  
            f"Channel ID: {context.activity.channel_id}\n"  
            f"Timestamp: {context.activity.timestamp}"  
        )  
  
        task_data = {  
            "fields": {  
                "project": {"key": project_name},  
                "summary": subject,  
                "description": {  
                    "type": "doc",  
                    "version": 1,  
                    "content": [  
                        {  
                            "type": "paragraph",  
                            "content": [  
                                {  
                                    "type": "text",  
                                    "text": description_text  
                                }  
                            ]  
                        }  
                    ]  
                },  
                "issuetype": {"name": "Task"},  
                "parent": {"id": await get_issue_id(parent_key)},  
                "assignee": {"accountId": default_account_id},  
                "labels": [default_label_title]  
            }  
        }  
  
        issue = jira.create_issue(fields=task_data['fields'])  
        return f"Task {issue.key} has been created under {parent_key} with the subject: {subject}. You can view the task [here]({jira_server}/browse/{issue.key})."  
    except JIRAError as e:  
        logging.error(f"Error creating JIRA task: {e}")  
        return f"An error occurred while creating the JIRA task: {e}"  
  
async def get_issue_id(issue_key):  
    try:  
        issue = jira.issue(issue_key)  
        return issue.id  
    except JIRAError as e:  
        logging.error(f"Error fetching issue ID: {e}")  
        raise  
