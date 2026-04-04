import os
from peewee import PostgresqlDatabase
from app.models.url import URL

db = PostgresqlDatabase(
    os.getenv('DATABASE_NAME', 'hackathon_db'),
    user=os.getenv('DATABASE_USER', 'assolabasova'),
    password=os.getenv('DATABASE_PASSWORD', ''),
    host=os.getenv('DATABASE_HOST', 'localhost'),
    port=int(os.getenv('DATABASE_PORT', 5432))
)

URL._meta.database = db

if __name__ == '__main__':
    db.connect()
    db.create_tables([URL])
    print("✅ Created table: urls")
    db.close()
