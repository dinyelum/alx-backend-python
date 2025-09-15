"""
Objective: create a decorator that retries database operations if they fail due to transient errors

Instructions:
Complete the script below by implementing a retry_on_failure(retries=3, delay=2) decorator that retries the function of a certain number of times if it raises an exception
"""

import time
import sqlite3
import functools


def with_db_connection(func):
    functools.wraps(func)

    def inner_wrapper(*args):
        try:
            # Creates the database file if it doesn't exist
            sqliteConnection = sqlite3.connect('your_database.db')
            args[0] = sqliteConnection
            args[1] = 1
            func(*args)
        except sqlite3.Error as err:
            print(f"Error: '{err}'")
        if sqliteConnection:
            sqliteConnection.close()
            print("Database connection closed.")
    return inner_wrapper


def retry_on_failure(func):
    functools.wraps(func)

    def inner_wrapper(**kargs):
        try:
            # Creates the database file if it doesn't exist
            sqliteConnection = sqlite3.connect('your_database.db')
            func(sqliteConnection, 1)
        except:
            retry = 1
            while retry <= kargs['retries']:
                time.sleep(kargs['delay'])
                func()
                retry += 1
            else:
                print("Connection failed after 3 retries.")
        return inner_wrapper()


@with_db_connection
@retry_on_failure(retries=3, delay=10)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# attempt to fetch users with automatic retry on failure


users = fetch_users_with_retry()
print(users)
