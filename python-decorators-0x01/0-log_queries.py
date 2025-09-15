"""
Objective: create a decorator that logs database queries executed by any function

Instructions:
Complete the code below by writing a decorator log_queries that logs the SQL query before executing it.

Prototype: def log_queries()
"""

# from datetime import datetime, print()


import sqlite3
import functools
import logging

# decorator to log SQL queries


def log_queries(func):
    functools.wraps(func)

    def inner_wrapper(*args, **kwargs):
        # log query
        # Google AI Overview: Python Log
        # https://stackoverflow.com/a/49580476/10153934
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(args[0])
        return func(*args, **kwargs)
    return inner_wrapper


@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results


# fetch users while logging the query
users = fetch_all_users(query="SELECT * FROM users")
