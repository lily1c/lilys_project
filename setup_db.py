import os
import csv
from peewee import PostgresqlDatabase
from dotenv import load_dotenv

load_dotenv()

db = PostgresqlDatabase(
    os.getenv('DATABASE_NAME', 'hackathon_db'),
    user=os.getenv('DATABASE_USER', 'postgres'),
    password=os.getenv('DATABASE_PASSWORD', ''),
    host=os.getenv('DATABASE_HOST', 'localhost'),
    port=int(os.getenv('DATABASE_PORT', 5432))
)

from app.models.user import User  # noqa: E402
from app.models.url import URL  # noqa: E402
from app.models.event import Event  # noqa: E402

User._meta.database = db
URL._meta.database = db
Event._meta.database = db

def setup():
    db.connect()
    db.drop_tables([Event, URL, User], safe=True)
    db.create_tables([User, URL, Event])
    print("✅ Created tables")

    # Load users
    with open('seed_data/users.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            User.get_or_create(id=row['id'], defaults={'username': row['username'], 'email': row['email']})
    print(f"✅ Loaded {User.select().count()} users")

    # Load URLs
    with open('seed_data/urls.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            URL.get_or_create(id=row['id'], defaults={'short_code': row['short_code'], 'original_url': row['original_url'], 'user_id': row.get('user_id') or None, 'title': row['title'], 'is_active': row['is_active'].lower() == 'true', 'created_at': row['created_at'], 'updated_at': row['updated_at']})
    print(f"✅ Loaded {URL.select().count()} URLs")

    # Load events
    with open('seed_data/events.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            Event.get_or_create(id=row['id'], defaults={'url_id': row.get('url_id') or None, 'user_id': row.get('user_id') or None, 'event_type': row['event_type'], 'timestamp': row['timestamp'], 'details': row.get('details')})
    print(f"✅ Loaded {Event.select().count()} events")
    
    # Recalibrate PostgreSQL auto-increment sequences
    db.execute_sql("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")
    db.execute_sql("SELECT setval('urls_id_seq', COALESCE((SELECT MAX(id) FROM urls), 1))")
    db.execute_sql("SELECT setval('events_id_seq', COALESCE((SELECT MAX(id) FROM events), 1))")

    db.close()
    print("🎉 Setup complete!")

if __name__ == '__main__':
    setup()
