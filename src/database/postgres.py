
import os
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()

class PostgresClient:

    def __init__(self):
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

    def connect(self):
        return psycopg.connect(
            host=self.DB_HOST,
            port=self.DB_PORT,
            dbname=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD
        )

    def insert_raw_match(self, match_id, game_json):
        with self.connect() as conn:
            with conn.cursor() as curr:
                curr.execute( 
                    ''' 
                    INSERT INTO raw_matches (match_id, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (match_id) DO NOTHING
                    '''
                    (match_id, Jsonb(game_json))
                )

    def get_existing_raw_match_ids(self):
        with self.connect() as conn:
            with conn.cursor() as curr:
                curr.execute( 
                    '''
                    SELECT match_id
                    FROM raw_matches
                    '''
                )

                rows = curr.fetchall()

        return {row[0] for row in rows}