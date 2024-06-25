# footer_utils.py  
import logging  
  
APP_VERSION = "1.624.0001"  
OPENAI_MODEL = "gpt4o"  

#   

#print out the openai_model value below ./
print(OPENAI_MODEL)  
def generate_footer(platform: str, response_time: float) -> str:  
    """Generates a footer string with application version, OpenAI model information, and response time.  
  
    Args:  
        platform (str): The platform for which the footer is being generated (e.g., "slack", "webchat").  
        response_time (float): The response time for the call.  
  
    Returns:  
        str: The formatted footer string.  
    """  
    logging.debug(f"Generating footer for platform: {platform} with response time: {response_time:.3f}s")  
    footer = f"App Version: {APP_VERSION} | OpenAI Model: {OPENAI_MODEL} | Response Time: {response_time:.3f}s"  
    if platform == "slack":  
        # Slack uses a different markdown syntax  
        #footer = f"`App Version`: _{APP_VERSION}_ | `OpenAI Model`: _{OPENAI_MODEL}_ | `Response Time`: _{response_time:.3f}s_"  
        footer = f"*App Version*: `{APP_VERSION}` | *OpenAI Model*: `{OPENAI_MODEL}` | *Response Time*: `{response_time:.3f}s`"  
    logging.debug(f"Generated footer: {footer}")  
    return footer  
