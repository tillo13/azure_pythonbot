import os  
import psycopg2  
from psycopg2 import sql, pool  
import logging  
  
# Load environment variables  
DATABASE_USER = os.environ.get("2023oct9_AZURE_POSTGRES_USER")  
DATABASE_HOST = os.environ.get("2023oct9_AZURE_POSTGRES_HOST")  
DATABASE_NAME = os.environ.get("2023oct9_AZURE_POSTGRES_DATABASE")  
DATABASE_PASSWORD = os.environ.get("2023oct9_AZURE_POSTGRES_PASSWORD")  
DATABASE_PORT = os.environ.get("2023oct9_AZURE_POSTGRES_PORT")  
DATABASE_INGRESS_TABLE = os.environ.get("2023oct9_AZURE_POSTGRES_DATABASE_INGRESS_TABLE")  
DATABASE_ROUTER_LOG_TABLE = os.environ.get("2023oct12_AZURE_POSTGRES_DATABASE_ROUTER_LOG_TABLE")  
  
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
  
def get_db_connection():  
    try:  
        connection = connection_pool.getconn()  
        if connection:  
            logging.debug("Successfully obtained connection from pool.")  
            return connection  
    except Exception as e:  
        logging.error(f"Error getting connection from pool: {e}")  
    return None  
  
def release_db_connection(connection):  
    try:  
        connection_pool.putconn(connection)  
        logging.debug("Successfully released connection back to pool.")  
    except Exception as e:  
        logging.error(f"Error releasing connection back to pool: {e}")  
  
def get_qa_from_database():  
    connection = get_db_connection()  
    if connection is None:  
        return None  
  
    try:  
        cursor = connection.cursor()  
        query = sql.SQL("SELECT question, answer FROM {} ORDER BY RANDOM() LIMIT 1").format(  
            sql.Identifier(DATABASE_INGRESS_TABLE)  
        )  
        cursor.execute(query)  
        result = cursor.fetchone()  
        cursor.close()  
        return result  
    except Exception as e:  
        logging.error(f"Error querying database: {e}")  
        return None  
    finally:  
        release_db_connection(connection)  
  
def bot_ingress_save_data_to_postgres(data, channel_id):  
    connection = get_db_connection()  
    if connection is None:  
        return  
  
    try:  
        cursor = connection.cursor()  
        query = sql.SQL("""  
            INSERT INTO {} (  
                channel_id, message_type, message_id, timestamp_from_endpoint,   
                local_timestamp_from_endpoint, local_timezone_from_endpoint,   
                service_url, from_id, from_name, conversation_id,   
                attachment_exists, recipient_id, recipient_name,   
                channeldata_webchat_id, channeldata_slack_app_id,   
                channeldata_slack_event_id, channeldata_slack_event_time,   
                channeldata_msteams_tenant_id, message_payload, created_via  
            ) VALUES (  
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s  
            ) RETURNING pk_id, message_id  
        """).format(sql.Identifier(DATABASE_INGRESS_TABLE))  
  
        cursor.execute(query, (  
            channel_id, data['type'], data['id'], data['timestamp'], data['localTimestamp'],   
            data['localTimezone'], data['serviceUrl'], data['from']['id'], data['from']['name'],   
            data['conversation']['id'], bool(data.get('attachments')), data['recipient']['id'],   
            data['recipient']['name'], data['channelData'].get('clientActivityID'),   
            data['channelData'].get('SlackMessage', {}).get('api_app_id'),   
            data['channelData'].get('SlackMessage', {}).get('event_id'),   
            data['channelData'].get('SlackMessage', {}).get('event_time'),   
            data['channelData'].get('tenant', {}).get('id'),   
            (data['text'] or "").substring(0, 2900), data.get('filename_ingress')  
        ))  
        connection.commit()  
        result = cursor.fetchone()  
        cursor.close()  
  
        if result:  
            logging.info(f"Data saved to bot_invoke_log with messageID: {result[1]}, and pk_id: {result[0]}")  
        else:  
            logging.info("No data returned after insert operation for botIngress path.")  
    except Exception as e:  
        logging.error(f"Failed to save data to Postgres for botIngress path: {e}")  
    finally:  
        release_db_connection(connection)  
  
# Similarly, other functions can be implemented based on your JavaScript code...  
  
if __name__ == "__main__":  
    # Example usage  
    qa = get_qa_from_database()  
    if qa:  
        logging.info(f"Question: {qa[0]}, Answer: {qa[1]}")  
    else:  
        logging.error("Failed to retrieve QA from database.")  
