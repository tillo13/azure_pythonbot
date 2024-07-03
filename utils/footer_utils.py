# footer_utils.py  
import logging  
  
APP_VERSION = "1.0703.0915"  

def generate_footer(platform: str, response_time: float, model_name: str = "gpt4o") -> str:  
    """Generates a footer string with application version, OpenAI model information, and response time.  

    Args:  
        platform (str): The platform for which the footer is being generated (e.g., "slack", "webchat").  
        response_time (float): The response time for the call.  
        model_name (str): The name of the OpenAI model used.  

    Returns:  
        str: The formatted footer string.  
    """  
    logging.debug(f"Generating footer for platform: {platform} with response time: {response_time:.3f}s and model: {model_name}")  
    footer = f"App Version: {APP_VERSION} | OpenAI Model: {model_name} | Response Time: {response_time:.3f}s"  
    if platform == "slack":  
        footer = f"*App Version*: `{APP_VERSION}` | *OpenAI Model*: `{model_name}` | *Response Time*: `{response_time:.3f}s`"  
    logging.debug(f"Generated footer: {footer}")  
    return footer  
