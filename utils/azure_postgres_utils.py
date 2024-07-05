import os  
import psycopg2  
from psycopg2 import sql  
import logging  
  
# Load environment variables  
DATABASE_USER = os.environ.get("2023oct9_AZURE_POSTGRES_USER")  
DATABASE_HOST = os.environ.get("2023oct9_AZURE_POSTGRES_HOST")  
DATABASE_NAME = os.environ.get("2023oct9_AZURE_POSTGRES_DATABASE")  
DATABASE_PASSWORD = os.environ.get("2023oct9_AZURE_POSTGRES_PASSWORD")  
DATABASE_PORT = os.environ.get("2023oct9_AZURE_POSTGRES_PORT")  
DATABASE_INGRESS_TABLE = os.environ.get("2023oct9_AZURE_POSTGRES_DATABASE_INGRESS_TABLE")  
  
def get_db_connection():  
    try:  
        connection = psycopg2.connect(  
            user=DATABASE_USER,  
            password=DATABASE_PASSWORD,  
            host=DATABASE_HOST,  
            port=DATABASE_PORT,  
            database=DATABASE_NAME  
        )  
        return connection  
    except Exception as e:  
        logging.error(f"Error connecting to the database: {e}")  
        return None  
  
def log_invocation_to_db(data):  
    connection = get_db_connection()  
    if connection is None:  
        return  
  
    try:  
        cursor = connection.cursor()  
        insert_query = sql.SQL("""  
            INSERT INTO {table} (  
                channel_id, message_type, message_id, timestamp_from_endpoint,   
                local_timestamp_from_endpoint, local_timezone_from_endpoint,   
                service_url, from_id, from_name, conversation_id,   
                attachment_exists, recipient_id, recipient_name,   
                channeldata_slack_app_id, channeldata_slack_event_id,   
                channeldata_slack_event_time, message_payload, interacting_user_id,   
                channeldata_slack_thread_ts  
            ) VALUES (  
                %(channel_id)s, %(message_type)s, %(message_id)s, %(timestamp_from_endpoint)s,   
                %(local_timestamp_from_endpoint)s, %(local_timezone_from_endpoint)s,   
                %(service_url)s, %(from_id)s, %(from_name)s, %(conversation_id)s,   
                %(attachment_exists)s, %(recipient_id)s, %(recipient_name)s,   
                %(channeldata_slack_app_id)s, %(channeldata_slack_event_id)s,   
                %(channeldata_slack_event_time)s, %(message_payload)s, %(interacting_user_id)s,   
                %(channeldata_slack_thread_ts)s  
            )  
        """).format(table=sql.Identifier(DATABASE_INGRESS_TABLE))  
  
        cursor.execute(insert_query, data)  
        connection.commit()  
        cursor.close()  
    except Exception as e:  
        logging.error(f"Error logging data to the database: {e}")  
    finally:  
        connection.close()  
