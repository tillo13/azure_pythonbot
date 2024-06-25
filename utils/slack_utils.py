import requests  
import logging  
import re  
from utils.footer_utils import generate_footer  
import json  
import os

SLACK_TOKEN = os.environ.get("APPSETTING_SLACK_TOKEN")    
  
SLACK_CHAT_URL = "https://slack.com/api/chat.postMessage"  
SLACK_CONVERSATIONS_REPLIES_URL = "https://slack.com/api/conversations.replies"  
SLACK_ADD_REACTION_URL = "https://slack.com/api/reactions.add"  
SLACK_REMOVE_REACTION_URL = "https://slack.com/api/reactions.remove"  

###mostly for special_commands_utils.py start #####
def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  
    
def find_latest_command_thread_ts(messages, command):  
    """  
    Find the latest thread_ts for the given command from the last 5 messages.  
    """  
    command = command.lower()  
    for message in messages:  
        if 'text' in message and message['text'].strip().lower().startswith(f"${command}"):  
            return message.get('thread_ts') or message.get('ts')  
    return None  
  

def extract_thread_ts(activity):  
    """  
    Extract the thread_ts from the activity.  
    """  
    return activity.channel_data.get('SlackMessage', {}).get('event', {}).get('thread_ts')  
###mostly for special_commands_utils.py end #####
  
def convert_openai_response_to_slack_mrkdwn(text):  
    #logging.debug(f"Original text: {text}")  
    logging.debug(f"passing through convert_openai_response_to_slack_mrkdwn def function... (debug by #uncommenting in slack_utils.py)")  
  
    # Handle code blocks first to avoid interfering with inline code  
    code_block_pattern = re.compile(r'```(.*?)```', re.DOTALL)  
    code_blocks = code_block_pattern.findall(text)  
    for i, block in enumerate(code_blocks):  
        placeholder = f"{{{{code_block_{i}}}}}"  
        text = text.replace(f"```{block}```", placeholder)  
  
    # Convert headers  
    text = re.sub(r'### (.*?)\n', r'```\1```\n', text)  
    #logging.debug(f"After converting headers: {text}")  
  
    # Convert bold text  
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)  
    #logging.debug(f"After converting bold text: {text}")  
  
    # Convert italic text  
    text = re.sub(r'_(.*?)_', r'_\1_', text)  
    #logging.debug(f"After converting italic text: {text}")  
  
    # Convert strikethrough text  
    text = re.sub(r'~(.*?)~', r'~\1~', text)  
    #logging.debug(f"After converting strikethrough text: {text}")  
  
    # Convert inline code  
    text = re.sub(r'`(.*?)`', r'`\1`', text)  
    #logging.debug(f"After converting inline code: {text}")  
  
    # Restore code blocks  
    for i, block in enumerate(code_blocks):  
        placeholder = f"{{{{code_block_{i}}}}}"  
        text = text.replace(placeholder, f"```{block}```")  
  
    # Convert lists  
    text = re.sub(r'^\* (.*?)$', r'• \1', text, flags=re.MULTILINE)  
    text = re.sub(r'^1\. (.*?)$', r'1. \1', text, flags=re.MULTILINE)  
    #logging.debug(f"After converting lists: {text}")  
  
    # Convert blockquotes  
    text = re.sub(r'^> (.*?)$', r'> \1', text, flags=re.MULTILINE)  
    #logging.debug(f"After converting blockquotes: {text}")  
  
    # Convert links  
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<\2|\1>', text)  
    #logging.debug(f"After converting links: {text}")  
  
    # Convert user mentions and channel links  
    text = re.sub(r'@(\w+)', r'<@\1>', text)  
    text = re.sub(r'#(\w+)', r'<#\1>', text)  
    #logging.debug(f"After converting user mentions and channel links: {text}")  
  
    #logging.debug(f"Converted text: {text}")  
    return text  
  
  
def convert_jira_response_to_slack_mrkdwn(issue_details):  
    """  
    Convert JIRA issue details to Slack Markdown format.  
    """  
    # Format child issues  
    child_issues_list = "\n".join([f"* `{child['key']}`: {child['summary']}" for child in issue_details['child_issues']])  
  
    # Format the response message  
    response_message = (  
        f"*Issue Key*: `{issue_details['key']}`\n\n"  
        f"*Issue Summary*: `{issue_details['summary']}`\n\n"  
        f"*Status*: `{issue_details['status']}`\n\n"  
        f"*Assignee*: `{issue_details['assignee']}`\n\n"  
        f"*Reporter*: `{issue_details['reporter']}`\n\n"  
        f"*Priority*: `{issue_details['priority']}`\n\n"  
        f"*Created*: `{issue_details['created']}`\n\n"  
        f"*Updated*: `{issue_details['updated']}`\n\n"  
        f"*Resolution Date*: `{issue_details['resolutiondate']}`\n\n"  
        f"*Labels*: `{', '.join(issue_details['labels'])}`\n\n"  
        f"*Components*: `{', '.join(issue_details['components'])}`\n\n"  
        f"*Issue Type*: `{issue_details['issuetype']}`\n\n"  
        f"*Project*: `{issue_details['project']}`\n\n"  
        f"*Votes*: `{issue_details['votes']}`\n\n"  
        f"*Comments*:\n" + "\n".join([f"* *{comment['author']}* \n_@({comment['created']})_: \n```\n{comment['body']}\n```\n\n" for comment in issue_details['comments']]) + "\n"  
        f"*Child Issues*:\n{child_issues_list} \n\n"  
        f"*Issue Description*:\n```{issue_details['description']}```\n\n"  
    )  
  
    return response_message  

  
def create_slack_message(main_message: str, footer: str, is_jira_response: bool = False) -> dict:  
    if is_jira_response:  
        formatted_message = convert_jira_response_to_slack_mrkdwn(main_message) + f"\n\n{footer}"  
    else:  
        formatted_message = convert_openai_response_to_slack_mrkdwn(main_message) + f"\n\n{footer}"  
  
    return {  
        "blocks": [  
            {  
                "type": "section",  
                "text": {  
                    "type": "mrkdwn",  
                    "text": formatted_message  
                }  
            },  
            {  
                "type": "divider"  
            },  
            {  
                "type": "context",  
                "elements": [  
                    {  
                        "type": "mrkdwn",  
                        "text": f"\n{footer}\n" 
                    }  
                ]  
            }  
        ]  
    }  
  
def add_reaction_to_message(token, channel, timestamp, name):  
    headers = {  
        "Content-Type": "application/json",  
        "Authorization": f"Bearer {token}"  
    }  
    payload = {  
        "channel": channel,  
        "timestamp": timestamp,  
        "name": name  
    }  
  
    try:  
        response = requests.post(SLACK_ADD_REACTION_URL, headers=headers, json=payload)  
        response_data = response.json()  
        logging.debug(f"Response from Slack (reactions.add): {response_data}")  
        if not response_data.get("ok"):  
            error_message = response_data.get("error", "Unknown error")  
            logging.error(f"Error adding reaction to Slack message: {response_data}")  
            return {"ok": False, "error": error_message}  
        else:  
            return response_data  
    except requests.exceptions.RequestException as e:  
        logging.error(f"Exception occurred while adding reaction to Slack message: {e}")  
        return {"ok": False, "error": "An error occurred while trying to add reaction to Slack message. Please try again later."}  
  
def remove_reaction_from_message(token, channel, timestamp, name):  
    headers = {  
        "Content-Type": "application/json",  
        "Authorization": f"Bearer {token}"  
    }  
    payload = {  
        "channel": channel,  
        "timestamp": timestamp,  
        "name": name  
    }  
  
    try:  
        response = requests.post(SLACK_REMOVE_REACTION_URL, headers=headers, json=payload)  
        response_data = response.json()  
        logging.debug(f"Response from Slack (reactions.remove): {response_data}")  
        if not response_data.get("ok"):  
            error_message = response_data.get("error", "Unknown error")  
            logging.error(f"Error removing reaction from Slack message: {response_data}")  
            return {"ok": False, "error": error_message}  
        else:  
            return response_data  
    except requests.exceptions.RequestException as e:  
        logging.error(f"Exception occurred while removing reaction from Slack message: {e}")  
        return {"ok": False, "error": "An error occurred while trying to remove reaction from Slack message. Please try again later."}  
  
def split_message_into_chunks(message: str, max_length: int) -> list:  
    """Split a message into chunks that are within the specified max length."""  
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]  



def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  





def get_last_5_messages(token, channel):  
    headers = {  
        "Content-Type": "application/x-www-form-urlencoded",  
        "Authorization": f"Bearer {token}"  
    }  
  
    params = {  
        "channel": channel,  
        "limit": 5  
    }  
  
    try:  
        response = requests.get('https://slack.com/api/conversations.history', headers=headers, params=params)  
        response_data = response.json()  
        if response_data.get("ok"):  
            return response_data.get("messages", [])  
        else:  
            logging.error(f"Error retrieving messages: {response_data.get('error', 'Unknown error')}")  
            return []  
    except requests.exceptions.RequestException as e:  
        logging.error(f"Exception occurred while retrieving messages: {e}")  
        return []  


def post_message_to_slack(token, channel, text, blocks=None, thread_ts=None):  
    headers = {  
        "Content-Type": "application/json",  
        "Authorization": f"Bearer {token}"  
    }  
  
    # Slack block text limit is 3000 characters  
    MAX_BLOCK_TEXT_LENGTH = 3000  
  
    # Split the text into chunks if it exceeds the limit  
    chunks = split_message_into_chunks(text, MAX_BLOCK_TEXT_LENGTH)  
  
    responses = []  
  
    for chunk in chunks:  
        payload = {  
            "channel": channel,  
            "text": chunk,  # This is required for fallback in case blocks are not supported  
            "mrkdwn": True,  
            "thread_ts": thread_ts  # Ensure thread_ts is included in the payload  
        }  
        if blocks:  
            # Adjust the blocks to contain only the current chunk  
            chunk_blocks = [{  
                "type": "section",  
                "text": {  
                    "type": "mrkdwn",  
                    "text": chunk  
                }  
            }] + blocks[1:]  # Keep the rest of the blocks unchanged  
            payload["blocks"] = chunk_blocks  
  
        logging.debug(f"Payload to Slack: {json.dumps(payload, indent=2)}")  
  
        try:  
            response = requests.post(SLACK_CHAT_URL, headers=headers, json=payload)  
            response_data = response.json()  
            logging.debug(f"Response from Slack: {response_data}")  
            if not response_data.get("ok"):  
                error_message = response_data.get("error", "Unknown error")  
                logging.error(f"Error posting message to Slack: {response_data}")  
  
                # Provide a user-friendly message based on the error  
                user_friendly_message = f"Failed to post message to Slack: {error_message}"  
                if "invalid_blocks" in error_message:  
                    user_friendly_message += " (The message content may be too long or improperly formatted.)"  
                elif "channel_not_found" in error_message:  
                    user_friendly_message += " (The specified Slack channel was not found.)"  
  
                responses.append({"ok": False, "error": user_friendly_message})  
                break  # Stop sending further chunks if there's an error  
            else:  
                responses.append(response_data)  
        except requests.exceptions.RequestException as e:  
            logging.error(f"Exception occurred while posting message to Slack: {e}")  
            responses.append({"ok": False, "error": "An error occurred while trying to post the message to Slack. Please try again later."})  
            break  # Stop sending further chunks if there's an error  
  
    return responses  

  
def get_conversation_replies(token, channel, thread_ts):  
    headers = {  
        "Content-Type": "application/json",  
        "Authorization": f"Bearer {token}"  
    }  
  
    params = {  
        "channel": channel,  
        "ts": thread_ts  
    }  
  
    try:  
        response = requests.get(SLACK_CONVERSATIONS_REPLIES_URL, headers=headers, params=params)  
        response_data = response.json()  
  
        #logging.debug(f"Response from Slack (conversations.replies): {response_data}")  
        logging.debug(f"Response from Slack (conversations.replies) showing threading happening (debug by #uncommenting in slack_utils.py)")  
  
        if not response_data.get("ok"):  
            error_message = response_data.get("error", "Unknown error")  
            logging.error(f"Error fetching conversation replies from Slack: {response_data}")  
            return {"ok": False, "error": error_message}  
        else:  
            return response_data  
    except requests.exceptions.RequestException as e:  
        logging.error(f"Exception occurred while fetching conversation replies from Slack: {e}")  
        return {"ok": False, "error": "An error occurred while trying to fetch conversation replies from Slack. Please try again later."}  
  
def create_slack_message(main_message: str, footer: str, is_jira_response: bool = False) -> dict:  
    if is_jira_response:  
        formatted_message = convert_jira_response_to_slack_mrkdwn(main_message) + f"\n\n{footer}"  
    else:  
        formatted_message = convert_openai_response_to_slack_mrkdwn(main_message) + f"\n\n{footer}"  
  
    return {  
        "blocks": [  
            {  
                "type": "section",  
                "text": {  
                    "type": "mrkdwn",  
                    "text": formatted_message  
                }  
            },  
            {  
                "type": "divider"  
            },  
            {  
                "type": "context",  
                "elements": [  
                    {  
                        "type": "mrkdwn",  
                        "text": footer  
                    }  
                ]  
            }  
        ]  
    }  
  
def parse_chat_history(conversation_history, bot_user_id):  
    """Format chat history as a list of message dictionaries with role and content."""  
    chat_history = []  
    if conversation_history:  
        for msg in conversation_history:  
            role = "user" if msg["user"] != bot_user_id else "assistant"  
            chat_history.append({"role": role, "content": msg["text"]})  
    else:  
        # If no history, set the system message as the first and only message  
        chat_history.append({"role": "system", "content": "This is the first and only message in this chat."})  
  
    # Log the formatted chat history  
    logging.debug(f"Formatted chat history: {chat_history}")  
    return chat_history  
