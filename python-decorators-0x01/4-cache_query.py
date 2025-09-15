"""
Objective: create a decorator that caches the results of a database queries inorder to avoid redundant calls

Instructions:
Complete the code below by implementing a decorator cache_query(func) that caches query results based on the SQL query string
"""

import time
import sqlite3
import functools


query_cache = {}


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


def cache_query(func):
    functools.wraps(func)

    def inner_wrapper(*args):
        if args[1] in query_cache:
            print(
                f"Retrieving product details for ID: '{args[1]}' from cache...")

            return query_cache[args[1]]
        else:
            # database query
            print(
                f"Fetching product details for ID: '{args[1]}' from database...")

            details = func(*args)

            query_cache[args[1]] = details
            # return details
    return inner_wrapper


@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# First call will cache the result
users = fetch_users_with_cache(query="SELECT * FROM users")

# Second call will use the cached result
users_again = fetch_users_with_cache(query="SELECT * FROM users")
