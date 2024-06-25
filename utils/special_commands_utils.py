import re  
import os
import time  
from botbuilder.core import TurnContext  
import logging  
from utils.jira_utils import fetch_issue_details  
from utils.footer_utils import generate_footer  
from utils.slack_utils import create_slack_message  
from utils.slack_utils import post_message_to_slack  # Import this function  
  
def extract_jira_issue_key(input_str):  
    """ Extracts the JIRA issue key from a given string. """  
    issue_key_pattern = re.compile(r'[A-Z]+-\d+')  
    if "browse" in input_str:  
        match = issue_key_pattern.search(input_str)  
        if match:  
            return match.group(0)  
    else:  
        match = issue_key_pattern.match(input_str)  
        if match:  
            return match.group(0)  
    return None  
  
async def handle_special_commands(turn_context: TurnContext) -> bool:  
    """ Handle special commands starting with '$'. """  
    user_message = turn_context.activity.text.strip()  
    platform = turn_context.activity.channel_id  # Get the platform (e.g., "slack", "webchat")  
  
    if user_message.startswith('$'):  
        command_parts = user_message[1:].split(maxsplit=1)  # Split the command into parts  
        command = command_parts[0].lower()  # The main command (e.g., 'jira')  
  
        # Extract thread_ts if available  
        thread_ts = turn_context.activity.channel_data.get("SlackMessage", {}).get("thread_ts") or turn_context.activity.channel_data.get("SlackMessage", {}).get("ts")  
  
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
  
            # Post the help message to Slack  
            slack_message = create_slack_message(help_message, "")  
            response_data_list = post_message_to_slack(  
                token=os.environ.get("APPSETTING_SLACK_TOKEN"),  
                channel=turn_context.activity.conversation.id.split(":")[2],  # Extract channel_id  
                text=help_message,  
                blocks=slack_message['blocks'],  
                thread_ts=thread_ts  # Pass the thread_ts  
            )  
  
            for response_data in response_data_list:  
                if not response_data.get("ok"):  
                    await turn_context.send_activity(response_data.get("error", "An error occurred while posting the message to Slack."))  
                    break  
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
