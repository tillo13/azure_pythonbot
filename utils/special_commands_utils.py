import time  
from botbuilder.core import TurnContext  
import logging  
from utils.jira_utils import fetch_issue_details  
from utils.footer_utils import generate_footer  
from utils.slack_utils import create_slack_message  
  
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
        command_parts = user_message[1:].split()  # Split the command into parts  
        command = command_parts[0].lower()  # The main command (e.g., 'jira')  
  
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
                f"**$test**: \\`TBD, but something we'll put here...\\`\n\n"  
                f"**$formats**: \\`Displays formatting values that work for Slack.\\`\n\n"  
                f"**$jira <issue_key>**: \\`Fetches and displays details of the specified JIRA issue.\\`\n\n"  
            )  
            await turn_context.send_activity(help_message)  
        elif command == "jira" and len(command_parts) > 1:  
            issue_key = command_parts[1]  
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
            await turn_context.send_activity(f"I don't understand that command: {command}")  
  
        return True  
  
    return False  
