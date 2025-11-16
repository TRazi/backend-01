import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Check django_migrations table
cursor.execute("SELECT * FROM django_migrations")
migrations = cursor.fetchall()
print(f'All migrations ({len(migrations)} total):')
for m in migrations:
    print(f'  {m}')

conn.close()
