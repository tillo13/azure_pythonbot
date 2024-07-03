import json  
import os  
import logging  

APPROVED_USERS_FILE = os.path.join(os.path.dirname(__file__), 'approved_users.json')  

def load_approved_users():  
    try:  
        with open(APPROVED_USERS_FILE, 'r') as file:  
            data = json.load(file)  
            return data.get("approved_users", [])  
    except FileNotFoundError:  
        logging.error(f"File {APPROVED_USERS_FILE} not found.")  
        return []  
    except json.JSONDecodeError as e:  
        logging.error(f"Error decoding JSON from {APPROVED_USERS_FILE}: {e}")  
        return []  
    except Exception as e:  
        logging.error(f"An error occurred while loading approved users: {e}")  
        return []  

def is_user_approved(user_id):  
    approved_users = load_approved_users()  
    if user_id in approved_users:  
        logging.info(f"User {user_id} is approved.")  
        return True  
    else:  
        logging.info(f"User {user_id} is not approved.")  
        return False  
