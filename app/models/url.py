import datetime
from peewee import CharField, BooleanField, DateTimeField, IntegerField, SQL
from app.database import BaseModel

class URL(BaseModel):
    user_id = IntegerField(null=True)
    short_code = CharField(max_length=10, unique=True, index=True)
    original_url = CharField(max_length=2048)
    title = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now, constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    updated_at = DateTimeField(default=datetime.datetime.now, constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        table_name = 'urls'
