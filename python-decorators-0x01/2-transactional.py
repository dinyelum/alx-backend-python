"""
Objective: create a decorator that manages database transactions by automatically committing or rolling back changes

Instructions:
Complete the script below by writing a decorator transactional(func) that ensures a function running a database operation is wrapped inside a transaction.If the function raises an error, rollback; otherwise commit the transaction.
Copy the with_db_connection created in the previous task into the script
"""

import sqlite3
import functools


def transactional(func):
    functools.wraps(func)

    def inner_wrapper(*args, **kwargs):
        conn = None
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()

            cursor.execute("BEGIN TRANSACTION")

            func(cursor, *args, **kwargs)

            # If no error, commit the transaction
            conn.commit()
            print("Transaction committed successfully.")

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
                print(f"Transaction rolled back due to error: {e}")
        except Exception as e:
            if conn:
                conn.rollback()
                print(f"Transaction rolled back due to unexpected error: {e}")
        finally:
            if conn:
                conn.close()
    return inner_wrapper


def with_db_connection(func):
    functools.wraps(func)

    def inner_wrapper():
        try:
            # Creates the database file if it doesn't exist
            sqliteConnection = sqlite3.connect('your_database.db')
            func(sqliteConnection, 1)
        except sqlite3.Error as err:
            print(f"Error: '{err}'")
        if sqliteConnection:
            sqliteConnection.close()
            print("Database connection closed.")
        return inner_wrapper()


@with_db_connection
@transactional
def update_user_email(conn, user_id, new_email):
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = ? WHERE id = ?",
                   (new_email, user_id))
# Update user's email with automatic transaction handling


update_user_email(user_id=1, new_email='Crawford_Cartwright@hotmail.com')
