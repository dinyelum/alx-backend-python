"""
Objective: create a decorator that automatically handles opening and closing database connections

Instructions:
Complete the script below by Implementing a decorator with_db_connection that opens a database connection, passes it to the function and closes it afterword
"""

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


@with_db_connection
def get_user_by_id(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()
# Fetch user by ID with automatic connection handling


user = get_user_by_id(user_id=1)
print(user)
