import os
import csv
from peewee import PostgresqlDatabase

db = PostgresqlDatabase(
    os.getenv('DATABASE_NAME', 'hackathon_db'),
    user=os.getenv('DATABASE_USER', 'assolabasova'),
    password=os.getenv('DATABASE_PASSWORD', ''),
    host=os.getenv('DATABASE_HOST', 'localhost'),
    port=int(os.getenv('DATABASE_PORT', 5432))
)

from app.models.user import User
from app.models.url import URL
from app.models.event import Event

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
            User.create(id=row['id'], username=row['username'], email=row['email'], created_at=row['created_at'])
    print(f"✅ Loaded {User.select().count()} users")

    # Load urls
    with open('seed_data/urls.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            URL.create(id=row['id'], user_id=row['user_id'], short_code=row['short_code'], original_url=row['original_url'], title=row.get('title'), is_active=row.get('is_active','True').lower()=='true', created_at=row['created_at'], updated_at=row.get('updated_at', row['created_at']))
    print(f"✅ Loaded {URL.select().count()} URLs")

    # Load events
    with open('seed_data/events.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            Event.create(id=row['id'], url_id=row.get('url_id'), user_id=row.get('user_id'), event_type=row['event_type'], timestamp=row['timestamp'], details=row.get('details'))
    print(f"✅ Loaded {Event.select().count()} events")

    db.close()
    print("🎉 Setup complete!")

if __name__ == '__main__':
    setup()
