import re  
import time  
from botbuilder.core import TurnContext  
import logging  
from utils.jira_utils import fetch_issue_details  
from utils.footer_utils import generate_footer  
from utils.slack_utils import create_slack_message  
  
JIRA_BASE_URL = "https://teradata-pe.atlassian.net/"  
  
def extract_issue_key(input_str):  
    """  
    Extracts the JIRA issue key from a given string.  
    """  
    # Regular expression to match JIRA issue key  
    issue_key_pattern = re.compile(r'[A-Z]+-\d+')  
      
    # Check if the input is a URL and extract the issue key  
    if JIRA_BASE_URL in input_str:  
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
    Handle special commands starting with '$' or specific URLs.  
  
    Args:  
        turn_context (TurnContext): The context object for the turn.  
  
    Returns:  
        bool: True if a special command was handled, False otherwise.  
    """  
    user_message = turn_context.activity.text.strip()  
    platform = turn_context.activity.channel_id  # Get the platform (e.g., "slack", "webchat")  
    thread_ts = turn_context.activity.conversation.id  # Thread timestamp for Slack threading  
  
    # Check if the input is a special command or a specific JIRA URL  
    if user_message.startswith('$') or JIRA_BASE_URL in user_message:  
        command_parts = user_message[1:].split(maxsplit=1) if user_message.startswith('$') else [None, user_message]  # Split the command into parts  
        command = command_parts[0].lower() if command_parts[0] else "jira"  # The main command (e.g., 'jira')  
  
        if command == "test":  
            await turn_context.send_activity("special test path invoked!", thread_ts=thread_ts)  
        elif command == "formats":  
            formatting_message = (  
                "*Formatting Values*:\n\n"  
                "* Bold text: **this is bold with 2 slash n and 2 stars** \n\n"  
                "* Strikethrough text: ~this is strikethrough~ \n\n"  
                "* Italic text: _this is italic with 2 slash n_ \n\n"  
                "* Inline code: \\`backslash before backtick`\n\n"  
                "* Code block:\n```\nthis is a code block with newline inside\n```\n\n"  
            )  
            await turn_context.send_activity(formatting_message, thread_ts=thread_ts)  
        elif command == "help":  
            help_message = (  
                f"**Commands Available**:\n\n"  
                f"**$test**: \\`Invokes a special test path.\\`\n\n"  
                f"**$formats**: \\`Displays formatting values that work for Slack.\\`\n\n"  
                f"**$jira <issue_key> or <JIRA URL>**: \\`Fetches and displays details of the specified JIRA issue.\\`\n\n"  
            )  
            await turn_context.send_activity(help_message, thread_ts=thread_ts)  
        elif command == "jira" and len(command_parts) > 1 or JIRA_BASE_URL in user_message:  
            input_str = command_parts[1] if len(command_parts) > 1 else user_message  
            issue_key = extract_issue_key(input_str)  
            if issue_key:  
                start_time = time.time()  # Start timing the response  
                try:  
                    issue_details = await fetch_issue_details(issue_key)  
                    response_time = time.time() - start_time  
                    footer = generate_footer(platform, response_time)  
  
                    # Create Slack message with the JIRA response  
                    slack_message = create_slack_message(issue_details, footer, is_jira_response=True)  
  
                    await turn_context.send_activity(slack_message['blocks'][0]['text']['text'], thread_ts=thread_ts)  
                except Exception as err:  
                    await turn_context.send_activity(f"Error fetching JIRA issue: {err}", thread_ts=thread_ts)  
            else:  
                await turn_context.send_activity("Invalid JIRA issue key or URL.", thread_ts=thread_ts)  
        else:  
            await turn_context.send_activity(f"I don't understand that command: {command}", thread_ts=thread_ts)  
  
        return True  
  
    return False  
