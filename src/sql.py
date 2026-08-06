from mysql.connector import connection
from os import getenv


SQL_CONN_PARAMS = {"user": getenv("SQL_USER"),
                   "password": getenv("SQL_PASSWORD"),
                   "host": "localhost",
                   "database": "discord"}


def connect_to_sql_database():
    try:
        return connection.MySQLConnection(**SQL_CONN_PARAMS)
    except Exception as e:
        print(f"ERROR: Database connection failed with error:\n{e}.")
        raise
