from peewee import CharField, IntegerField, DateTimeField, SQL

from app.database import BaseModel


class URL(BaseModel):
    """Shortened URL model."""
    short_code = CharField(max_length=10, unique=True, index=True)
    original_url = CharField(max_length=2048)
    hits = IntegerField(default=0)
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    class Meta:
        table_name = 'urls'
