import os  
import psycopg2  
from psycopg2 import pool  
import logging  
from datetime import datetime, timezone  
  
# Configure logging  
logging.basicConfig(level=logging.DEBUG)  
  
# Load environment variables with defaults  
DATABASE_USER = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_USER", "default_user")  
DATABASE_HOST = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_HOST", "localhost")  
DATABASE_NAME = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_DATABASE", "default_db")  
DATABASE_PASSWORD = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_PASSWORD", "default_password")  
DATABASE_PORT = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_PORT", "5432")  
DATABASE_INGRESS_TABLE = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_DATABASE_INGRESS_TABLE", "default_table")  
  
# Print environment variable values for verification  
print("DATABASE_USER:", DATABASE_USER)  
print("DATABASE_HOST:", DATABASE_HOST)  
print("DATABASE_NAME:", DATABASE_NAME)  
print("DATABASE_PASSWORD:", DATABASE_PASSWORD)  
print("DATABASE_PORT:", DATABASE_PORT)  
print("DATABASE_INGRESS_TABLE:", DATABASE_INGRESS_TABLE)  
  
# Log the connection parameters (excluding sensitive information)  
logging.debug(f"DATABASE_HOST: {DATABASE_HOST}, DATABASE_PORT: {DATABASE_PORT}, DATABASE_USER: {DATABASE_USER}, DATABASE_NAME: {DATABASE_NAME}")  
  
# Initialize connection pool  
try:  
    connection_pool = psycopg2.pool.SimpleConnectionPool(  
        1, 20, user=DATABASE_USER, password=DATABASE_PASSWORD,  
        host=DATABASE_HOST, port=DATABASE_PORT,  
        database=DATABASE_NAME, sslmode='require'  
    )  
    if connection_pool:  
        logging.info("Connection pool created successfully.")  
except Exception as e:  
    logging.error(f"Error creating connection pool: {e}")  
    connection_pool = None  # Ensure the rest of the app can continue even if the pool fails  
  
def test_db_connection():  
    try:  
        connection = psycopg2.connect(  
            user=DATABASE_USER,  
            password=DATABASE_PASSWORD,  
            host=DATABASE_HOST,  
            port=DATABASE_PORT,  
            database=DATABASE_NAME,  
            sslmode='require'  
        )  
        logging.info("Successfully connected to the database using direct connection.")  
        connection.close()  
    except Exception as e:  
        logging.error(f"Direct connection test failed: {e}")  
  
test_db_connection()  
  
def get_db_connection():  
    if connection_pool is None:  
        logging.error("Connection pool is not available.")  
        return None  
  
    try:  
        connection = connection_pool.getconn()  
        if connection:  
            logging.debug("Successfully obtained connection from pool.")  
            return connection  
    except Exception as e:  
        logging.error(f"Error getting connection from pool: {e}")  
    return None  
  
def release_db_connection(connection):  
    if connection_pool is None:  
        logging.error("Connection pool is not available.")  
        return  
  
    try:  
        connection_pool.putconn(connection)  
        logging.debug("Successfully released connection back to pool.")  
    except Exception as e:  
        logging.error(f"Error releasing connection back to pool: {e}")  
  
def log_invocation_to_db(data):  
    connection = get_db_connection()  
    if connection is None:  
        logging.error("No database connection available. Skipping log invocation.")  
        return  
  
    try:  
        cursor = connection.cursor()  
        query = f"""  
            INSERT INTO {DATABASE_INGRESS_TABLE} (  
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
            ) RETURNING pk_id, message_id  
        """  
        logging.debug(f"Executing query: {query}")  
        logging.debug(f"With data: {data}")  
        # Ensure local_timestamp_from_endpoint is a datetime object  
        data['local_timestamp_from_endpoint'] = convert_timestamp_to_datetime(data['local_timestamp_from_endpoint'])  
        cursor.execute(query, data)  
        connection.commit()  
        result = cursor.fetchone()  
        cursor.close()  
  
        if result:  
            logging.info(f"Data saved to bot_invoke_log with messageID: {result[1]}, and pk_id: {result[0]}")  
        else:  
            logging.info("No data returned after insert operation for Slack invocation.")  
    except Exception as e:  
        logging.error(f"Failed to save Slack data to Postgres: {e}")  
    finally:  
        release_db_connection(connection)  
  
# Function to convert timestamp to datetime  
def convert_timestamp_to_datetime(timestamp):  
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)  
  
def save_or_fetch_file_hash(hash_value, file_payload, uploaded_by):  
    connection = get_db_connection()  
    if connection is None:  
        logging.error("No database connection available. Skipping save or fetch file operation.")  
        return None  
  
    try:  
        cursor = connection.cursor()  
          
        # Check if the hash value already exists  
        query_check = "SELECT pk_id, file_payload FROM public.bot_file_upload_hashes WHERE hash_value = %s"  
        cursor.execute(query_check, (hash_value,))  
        existing_record = cursor.fetchone()  
  
        if existing_record:  
            logging.info(f"File with hash {hash_value} already exists. Fetching existing record.")  
            return existing_record[1]  # Return the existing file payload  
          
        # Insert the new file record  
        query_insert = """  
            INSERT INTO public.bot_file_upload_hashes (hash_value, file_payload, uploaded_by)  
            VALUES (%s, %s, %s) RETURNING pk_id  
        """  
        cursor.execute(query_insert, (hash_value, psycopg2.Binary(file_payload), uploaded_by))  
        connection.commit()  
        pk_id = cursor.fetchone()[0]  
        cursor.close()  
        logging.info(f"File with hash {hash_value} saved successfully with pk_id: {pk_id}")  
        return None  
  
    except Exception as e:  
        logging.error(f"Failed to save or fetch file: {e}")  
        return None  
    finally:  
        release_db_connection(connection)  
