import os
import logging
import psycopg

from dotenv import load_dotenv
from psycopg.types.json import Jsonb


# Create a module-specific logger for database-related events.
logger = logging.getLogger(__name__)


# Load PostgreSQL connection credentials from the project's .env file.
load_dotenv()


class PostgresClient:
    """
    Handles PostgreSQL connections and database operations for the
    Riot data pipeline.

    Provides methods for storing raw Riot match payloads, tracking players,
    and maintaining player-to-match relationships.
    """

    def __init__(self):
        """
        Load PostgreSQL connection settings from environment variables.
        """

        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

    def connect(self):
        """
        Create and return a new PostgreSQL database connection.

        Returns:
            psycopg.Connection: Connection to the configured PostgreSQL
            database.
        """

        return psycopg.connect(
            host=self.DB_HOST,
            port=self.DB_PORT,
            dbname=self.DB_NAME,
            user=self.DB_USER,
            password=self.DB_PASSWORD
        )

    def insert_raw_match(self, match_id, game_json):
        """
        Insert a raw Riot match payload into raw_matches.

        Duplicate match IDs are ignored because each Riot match should
        only be stored once globally.

        Args:
            match_id: Unique Riot match identifier.
            game_json: Complete JSON response returned by the Riot API.
        """

        # Context managers automatically close the cursor and connection.
        # A successful connection block is committed automatically.
        with self.connect() as conn:
            with conn.cursor() as curr:

                curr.execute(
                    '''
                    INSERT INTO raw_matches (match_id, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (match_id) DO NOTHING
                    ''',
                    # Jsonb converts the Python dictionary into a value
                    # PostgreSQL can store in a JSONB column.
                    (match_id, Jsonb(game_json))
                )

    def get_existing_raw_match_ids(self):
        """
        Retrieve the IDs of all raw matches currently stored.

        Returns:
            set: Existing Riot match IDs.
        """

        with self.connect() as conn:
            with conn.cursor() as curr:

                curr.execute(
                    '''
                    SELECT match_id
                    FROM raw_matches
                    '''
                )

                rows = curr.fetchall()

        # Convert database rows such as [('MATCH_1',), ('MATCH_2',)]
        # into a set for efficient membership checks during ingestion.
        return {row[0] for row in rows}

    def upsert_tracked_player(self, puuid, game_name, tag_line):
        """
        Insert a tracked player or update their Riot ID information.

        PUUID is used as the stable player identifier. If the PUUID already
        exists, the current game name and tag line are updated.

        Args:
            puuid: Riot's unique identifier for the player.
            game_name: Current Riot ID game name.
            tag_line: Current Riot ID tag line.
        """

        with self.connect() as conn:
            with conn.cursor() as curr:

                curr.execute(
                    '''
                    INSERT INTO tracked_players (puuid, game_name, tag_line)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (puuid)
                    DO UPDATE SET
                        game_name = EXCLUDED.game_name,
                        tag_line = EXCLUDED.tag_line
                    ''',
                    (puuid, game_name, tag_line)
                )

    def insert_player_match(self, puuid, match_id):
        """
        Associate a tracked player with a Riot match.

        player_matches acts as a junction table between tracked players
        and raw matches. Duplicate player-match relationships are ignored.

        Args:
            puuid: Riot's unique identifier for the player.
            match_id: Riot match identifier to associate with the player.
        """

        with self.connect() as conn:
            with conn.cursor() as curr:

                curr.execute(
                    '''
                    INSERT INTO player_matches (puuid, match_id)
                    VALUES (%s, %s)
                    ON CONFLICT (puuid, match_id) DO NOTHING
                    ''',
                    (puuid, match_id)
                )

    def get_tracked_players(self):
        """
        Retrieve the PUUIDs of all players currently being tracked.

        Returns:
            set: PUUIDs for all tracked players.
        """

        with self.connect() as conn:
            with conn.cursor() as curr:

                curr.execute(
                    '''
                    SELECT puuid
                    FROM tracked_players
                    '''
                )

                rows = curr.fetchall()

        # Return a set so player existence checks can be performed efficiently.
        return {row[0] for row in rows}

    def get_existing_player_match_ids(self, puuid):
        """
        Retrieve all match IDs associated with a specific tracked player.

        This is separate from get_existing_raw_match_ids() because a raw
        match may already exist globally without yet being associated with
        the current player.

        Args:
            puuid: Riot's unique identifier for the tracked player.

        Returns:
            set: Match IDs already associated with the player.
        """

        with self.connect() as conn:
            with conn.cursor() as curr:

                # Parameterized SQL prevents the PUUID from being directly
                # interpolated into the SQL statement.
                curr.execute(
                    '''
                    SELECT match_id
                    FROM player_matches
                    WHERE puuid = %s
                    ''',
                    # A trailing comma creates the one-element tuple expected
                    # by psycopg for a single SQL parameter.
                    (puuid,)
                )

                rows = curr.fetchall()

        return {row[0] for row in rows}