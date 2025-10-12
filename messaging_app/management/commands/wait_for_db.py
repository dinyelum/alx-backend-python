import time
import os
import MySQLdb
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    """Django command to wait for database to be available"""

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_conn = None
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get database configuration from environment
                db_host = os.getenv('DB_HOST', 'db')
                db_name = os.getenv('DB_NAME', 'messaging_db')
                db_user = os.getenv('DB_USER', 'django_user')
                db_password = os.getenv('DB_PASSWORD', 'secure_password_123')
                
                # Try to connect to MySQL
                db_conn = MySQLdb.connect(
                    host=db_host,
                    user=db_user,
                    passwd=db_password,
                    db=db_name,
                    port=3306
                )
                self.stdout.write(self.style.SUCCESS('Database available!'))
                if db_conn:
                    db_conn.close()
                return
            except Exception as e:
                self.stdout.write(f'Database unavailable, waiting 1 second... (Attempt {retry_count + 1}/{max_retries})')
                retry_count += 1
                time.sleep(1)
        
        self.stdout.write(self.style.ERROR('Could not connect to database after 30 seconds'))
        exit(1)