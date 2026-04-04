from peewee import CharField, DateTimeField, SQL
from app.database import BaseModel

class User(BaseModel):
    username = CharField(max_length=255)
    email = CharField(max_length=255, unique=True)
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        table_name = 'users'
