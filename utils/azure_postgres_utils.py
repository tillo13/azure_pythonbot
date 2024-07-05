import os  
import psycopg2  
from psycopg2 import sql, pool  
import logging  
  
# Configure logging  
logging.basicConfig(level=logging.DEBUG)  
  
# Load environment variables with defaults  
DATABASE_USER = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_USER", "default_user")  
DATABASE_HOST = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_HOST", "localhost")  
DATABASE_NAME = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_DATABASE", "default_db")  
DATABASE_PASSWORD = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_PASSWORD", "default_password")  
DATABASE_PORT = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_PORT", "5432")  
DATABASE_INGRESS_TABLE = os.environ.get("APPSETTING_2023oct9_AZURE_POSTGRES_DATABASE_INGRESS_TABLE", "default_table")  
  
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
        query = sql.SQL("""  
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
            ) RETURNING pk_id, message_id  
        """).format(sql.Identifier(DATABASE_INGRESS_TABLE))  
  
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
