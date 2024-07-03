import re  
import json  
import time  
from botbuilder.core import TurnContext  
import logging  
from utils.jira_utils import fetch_issue_details  
from utils.footer_utils import generate_footer  
from utils.slack_utils import create_slack_message, get_last_5_messages, post_message_to_slack, add_reaction_to_message, remove_reaction_from_message
import os  

from .person_search_utils import search_person  


SLACK_TOKEN = os.environ.get("APPSETTING_SLACK_TOKEN")  
  
def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  
  
def extract_jira_issue_key(input_str):  
    """  
    Extracts the JIRA issue key from a given string.  
    """  
    # Regular expression to match JIRA issue key (case-insensitive)  
    issue_key_pattern = re.compile(r'[A-Z]+-\d+', re.IGNORECASE)  
      
    # Check if the input is a URL and extract the issue key  
    if "browse" in input_str:  
        match = issue_key_pattern.search(input_str)  
        if match:  
            return match.group(0).upper()  # Convert to uppercase for consistency  
    else:  
        # Check if the input is a direct issue key  
        match = issue_key_pattern.match(input_str)  
        if match:  
            return match.group(0).upper()  # Convert to uppercase for consistency  
  
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
  

async def handle_special_commands(turn_context: TurnContext) -> bool:  
    user_message = turn_context.activity.text.strip().lower()  # Convert to lowercase  
    platform = turn_context.activity.channel_id  # Get the platform (e.g., "slack", "webchat")  
    token = os.environ.get("APPSETTING_SLACK_TOKEN")  
    if user_message.startswith('$'):  
        command_parts = user_message[1:].split(maxsplit=1)  # Split the command into parts  
        command = command_parts[0].lower()  # The main command (e.g., 'jira')  
        # Extract channel_id for logging messages  
        channel_id = extract_channel_id(turn_context.activity.conversation.id)  
        # Log the special command invocation  
        logging.debug(f"SPECIAL COMMAND INVOKED: {command} -- Invoking the last 5 slack messages in that thread")  
        # Extract thread_ts directly from the activity  
        thread_ts = extract_thread_ts(turn_context.activity) or turn_context.activity.channel_data.get('SlackMessage', {}).get('event', {}).get('ts')  
        if thread_ts:  
            logging.debug(f"Using thread_ts for response: {thread_ts}")  
        else:  
            logging.error("Unable to find thread_ts from the activity.")  
            thread_ts = turn_context.activity.timestamp  # Default to current message timestamp  
        # Add hourglass reaction  
        add_reaction_to_message(token, channel_id, thread_ts, "hourglass")  
        try:  
            # Handle special commands  
            if command == "test":  
                response_text = "special test path invoked!"  
                post_message_to_slack(token, channel_id, response_text, thread_ts=thread_ts)  
            elif command == "formats":  
                formatting_message = (  
                    "*Formatting Values*:\n\n"  
                    "* Bold text: *this is bold with 2 slash n and 1 star* \n\n"  
                    "* Strikethrough text: ~this is strikethrough~ \n\n"  
                    "* Italic text: _this is italic with 2 slash n_ \n\n"  
                    "* Inline code: `1 backslash before backtick`\n\n"  
                    "* Code block:\n```\nthis is a code block with newline inside\n```\n\n"  
                )  
                post_message_to_slack(token, channel_id, formatting_message, thread_ts=thread_ts)  
            elif command == "help":  
                help_message = (  
                    f"*Commands Available*:\n\n"  
                    f"*$test*: `Invokes a special test path.`\n\n"  
                    f"*$formats*: `Displays formatting values that work for Slack.`\n\n"  
                    f"*$jira <issue_key> or <JIRA URL>*: `Fetches and displays details of the specified JIRA issue.`\n\n"  
                    f"*$person <name>*: `Searches for the specified person and displays their information.`\n\n"  
                )  
                post_message_to_slack(token, channel_id, help_message, thread_ts=thread_ts)  
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
                        post_message_to_slack(token, channel_id, slack_message['blocks'][0]['text']['text'], thread_ts=thread_ts)  
                    except Exception as err:  
                        error_text = f"Error fetching JIRA issue: {err}"  
                        post_message_to_slack(token, channel_id, error_text, thread_ts=thread_ts)  
                else:  
                    invalid_key_text = "Invalid JIRA issue key or URL."  
                    post_message_to_slack(token, channel_id, invalid_key_text, thread_ts=thread_ts)  
            elif command == "person" and len(command_parts) > 1:  
                person_name = command_parts[1]  
                start_time = time.time()  # Start timing the response  
                try:  
                    search_results, model_name, input_tokens, output_tokens = await search_person(person_name)  
                    response_time = time.time() - start_time  
                    footer = generate_footer(platform, response_time, model_name, input_tokens, output_tokens)  
                    # Create Slack message with the person search results  
                    slack_message = create_slack_message(search_results, footer)  
                    post_message_to_slack(token, channel_id, slack_message['blocks'][0]['text']['text'], thread_ts=thread_ts)  
                except Exception as err:  
                    error_text = f"Error searching for person: {err}"  
                    post_message_to_slack(token, channel_id, error_text, thread_ts=thread_ts)  
            else:  
                unknown_command_text = f"I don't understand that command: {command}"  
                post_message_to_slack(token, channel_id, unknown_command_text, thread_ts=thread_ts)  
            # Remove hourglass and add greencheckmark reaction  
            remove_reaction_from_message(token, channel_id, thread_ts, "hourglass")  
            add_reaction_to_message(token, channel_id, thread_ts, "white_check_mark")  
        except Exception as e:  
            logging.error(f"Exception occurred while handling command: {e}")  
            post_message_to_slack(token, channel_id, f"An error occurred: {e}", thread_ts=thread_ts)  
            # Remove hourglass reaction in case of error  
            remove_reaction_from_message(token, channel_id, thread_ts, "hourglass")  
        return True  
    return False  
