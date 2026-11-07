
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

        if connection.is_connected():
            print("MySQL Connected Successfully!")
            return connection

    except mysql.connector.Error as error:
        print("Database Connection Error:", error)
        raise
