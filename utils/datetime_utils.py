# datetime_utils.py  
import time  
  
def get_current_time():  
    """Returns the current time in seconds since the Epoch."""  
    return time.time()  
  
def calculate_elapsed_time(start_time):  
    """Calculates the elapsed time from the start time to the current time.  
  
    Args:  
        start_time (float): The start time in seconds since the Epoch.  
  
    Returns:  
        float: The elapsed time in seconds.  
    """  
    return time.time() - start_time  
