import sqlite3


class ExecuteQuery:
    def __init__(self, db_name, query, params=None):
        self.db_name = db_name
        self.query = query
        self.params = params if params is not None else []
        self.conn = None
        self.cursor = None
        self.result = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            self.cursor.execute(self.query, self.params)
            self.result = self.cursor.fetchall()
            return self.result
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()


# Example Usage:
if __name__ == "__main__":
    # Create a dummy database for demonstration
    conn_setup = sqlite3.connect('users.db')
    cursor_setup = conn_setup.cursor()
    cursor_setup.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    ''')
    cursor_setup.execute(
        "INSERT INTO users (name, age) VALUES (?, ?)", ("Alice", 30))
    cursor_setup.execute(
        "INSERT INTO users (name, age) VALUES (?, ?)", ("Bob", 20))
    cursor_setup.execute(
        "INSERT INTO users (name, age) VALUES (?, ?)", ("Charlie", 35))
    conn_setup.commit()
    conn_setup.close()

    query_str = "SELECT * FROM users WHERE age > ?"
    parameter = 25

    with ExecuteQuery('users.db', query_str, (parameter,)) as results:
        if results:
            print("Query Results:")
            for row in results:
                print(row)
        else:
            print("No results or an error occurred during query execution.")

    # Clean up the dummy database
    import os
    os.remove('users.db')
