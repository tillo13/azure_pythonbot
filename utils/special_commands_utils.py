import re  
import json
import time  
from botbuilder.core import TurnContext  
import logging  
from utils.jira_utils import fetch_issue_details  
from utils.footer_utils import generate_footer  
from utils.slack_utils import create_slack_message, get_last_5_messages  

import os  
SLACK_TOKEN = os.environ.get("APPSETTING_SLACK_TOKEN")  
  
def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  
  
def get_parent_thread_ts(activity):  
    """Extracts and returns the parent thread timestamp (thread_ts) from the activity."""  
    event_data = activity.channel_data.get("SlackMessage", {}).get("event", {})  
    thread_ts = event_data.get("thread_ts")  
    if thread_ts:  
        print(f"*****THE PARENT THREAD TS (thread_ts) FOR THIS CONVERSATION IS {thread_ts}*******")  
        return thread_ts  
    else:  
        ts = event_data.get("ts")  
        if ts:  
            print(f"*****THE PARENT THREAD TS (just ts) FOR THIS CONVERSATION IS {ts}*******")  
            return ts  
        else:  
            logging.error("Both thread_ts and ts are None, cannot proceed.")  
            return None  

def extract_jira_issue_key(input_str):  
    """  
    Extracts the JIRA issue key from a given string.  
    """  
    # Regular expression to match JIRA issue key  
    issue_key_pattern = re.compile(r'[A-Z]+-\d+')  
      
    # Check if the input is a URL and extract the issue key  
    if "browse" in input_str:  
        match = issue_key_pattern.search(input_str)  
        if match:  
            return match.group(0)  
    else:  
        # Check if the input is a direct issue key  
        match = issue_key_pattern.match(input_str)  
        if match:  
            return match.group(0)  
      
    return None  

async def handle_special_commands(turn_context: TurnContext) -> bool:  
    """  
    Handle special commands starting with '$'.  
  
    Args:  
        turn_context (TurnContext): The context object for the turn.  
  
    Returns:  
        bool: True if a special command was handled, False otherwise.  
    """  
    user_message = turn_context.activity.text.strip()  
    platform = turn_context.activity.channel_id  # Get the platform (e.g., "slack", "webchat")  
  
    if user_message.startswith('$'):  
        command_parts = user_message[1:].split(maxsplit=1)  # Split the command into parts  
        command = command_parts[0].lower()  # The main command (e.g., 'jira')  
  
        # Extract channel_id and thread_ts for logging messages  
        channel_id = extract_channel_id(turn_context.activity.conversation.id)  
        thread_ts = get_parent_thread_ts(turn_context.activity)  
  
        # Log the special command invocation  
        logging.debug(f"SPECIAL COMMAND INVOKED: {command} -- Invoking the last 5 slack messages in that thread")  
  
        # Fetch and log the last 5 messages in the channel  
        last_5_messages = get_last_5_messages(SLACK_TOKEN, channel_id)  
        logging.debug(f"Last 5 messages in channel {channel_id}: {json.dumps(last_5_messages, indent=2)}")  
  
        # Handle special commands  
        if command == "test":  
            await turn_context.send_activity("special test path invoked!")  
        elif command == "formats":  
            formatting_message = (  
                "*Formatting Values*:\n\n"  
                "* Bold text: **this is bold with 2 slash n and 2 stars** \n\n"  
                "* Strikethrough text: ~this is strikethrough~ \n\n"  
                "* Italic text: _this is italic with 2 slash n_ \n\n"  
                "* Inline code: \\`backslash before backtick`\n\n"  
                "* Code block:\n```\nthis is a code block with newline inside\n```\n\n"  
            )  
            await turn_context.send_activity(formatting_message)  
        elif command == "help":  
            help_message = (  
                f"**Commands Available**:\n\n"  
                f"**$test**: \\`Invokes a special test path.\\`\n\n"  
                f"**$formats**: \\`Displays formatting values that work for Slack.\\`\n\n"  
                f"**$jira <issue_key> or <JIRA URL>**: \\`Fetches and displays details of the specified JIRA issue.\\`\n\n"  
            )  
            await turn_context.send_activity(help_message)  
        elif command == "jira" and len(command_parts) > 1:  
            input_str = command_parts[1]  
            issue_key = extract_jira_issue_key(input_str)  
            if issue_key:  
                start_time = time.time()  # Start timing the response  
                try:  
                    issue_details = await fetch_issue_details(issue_key)  
                    response_time = time.time() - start_time  
                    footer = generate_footer(platform, response_time)  
  
                    # Create Slack message with the JIRA response  
                    slack_message = create_slack_message(issue_details, footer, is_jira_response=True)  
  
                    await turn_context.send_activity(slack_message['blocks'][0]['text']['text'])  
                except Exception as err:  
                    await turn_context.send_activity(f"Error fetching JIRA issue: {err}")  
            else:  
                await turn_context.send_activity("Invalid JIRA issue key or URL.")  
        else:  
            await turn_context.send_activity(f"I don't understand that command: {command}")  
  
        return True  
  
    return False  
