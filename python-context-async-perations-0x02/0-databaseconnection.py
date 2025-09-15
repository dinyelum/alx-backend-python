import sqlite3


class DatabaseConnection:
    def __init__(self, db_name):
        """
        Initializes the DatabaseConnection with the specified database name.
        """
        self.db_name = db_name
        self.connection = None
        self.cursor = None

    def __enter__(self):
        """
        Establishes a database connection when entering the 'with' block.
        Returns the connection object.
        """
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            print(f"Database connection to '{self.db_name}' established.")
            return self.connection
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the database connection when exiting the 'with' block.
        Handles potential exceptions during the 'with' block's execution.
        """
        if self.connection:
            if exc_type:  # An exception occurred within the 'with' block
                self.connection.rollback()
                print(f"Transaction rolled back due to exception: {exc_val}")
            else:
                self.connection.commit()
                print("Transaction committed.")
            self.connection.close()
            print(f"Database connection to '{self.db_name}' closed.")
        return False  # Re-raise any exception that occurred


# Example Usage:
if __name__ == "__main__":
    with DatabaseConnection("my_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        cursor.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))

        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        print("Users in the database:", rows)

    print("\nAttempting an operation that might cause an error:")
    try:
        with DatabaseConnection("my_database.db") as conn:
            cursor = conn.cursor()
            # This will cause an error if 'id' is already primary key and we try to insert duplicate
            cursor.execute(
                "INSERT INTO users (id, name) VALUES (?, ?)", (1, "Charlie"))
    except sqlite3.IntegrityError as e:
        print(f"Caught expected error: {e}")
