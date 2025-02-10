from peewee import SqliteDatabase, CharField, FloatField, BooleanField, DateTimeField, Model, IntegerField
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME", "downloads.db")
db = SqliteDatabase(DATABASE_NAME)










class DownloadStatus(Model):
    fingerprint = CharField(primary_key=True)
    url = CharField()
    fpath = CharField()
    elapsed = FloatField(default=0.0)
    offset = IntegerField(default=0)
    length = IntegerField(default=0)
    last_speed = FloatField(default=0.0)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    is_paused = BooleanField(default=False)
    is_removed = BooleanField(default=False)

    class Meta:
        database = db

def initialize_database():
    db.connect()
    db.create_tables([DownloadStatus])

if __name__ == '__main__':
    initialize_database()
