import os
import logging

from dotenv import load_dotenv

from src.api.riot_client import RiotClient
from src.database.postgres import PostgresClient
from src.utils.logging_config import setup_logging


# Create a module-specific logger using this file's module name.
logger = logging.getLogger(__name__)


class MatchIngestion:
    """
    Coordinates ingestion of Riot match data into PostgreSQL.

    Uses RiotClient to retrieve match IDs and match payloads, and
    PostgresClient to store raw matches and player-match relationships.
    """

    def __init__(self, riot_client, db):
        """
        Initialize the ingestion service with Riot API and database clients.

        The tracked player is upserted when the ingestion service is created
        so the player exists before player-match relationships are inserted.
        """

        self.riot_client = riot_client
        self.db = db

        # Store the player's identifying information from RiotClient.
        self.puuid = self.riot_client.puuid
        self.game_name = self.riot_client.game_name
        self.tag_line = self.riot_client.tag_line

        # Insert the player if they do not exist, or update their Riot ID
        # information if the PUUID is already being tracked.
        self.db.upsert_tracked_player(
            self.puuid,
            self.game_name,
            self.tag_line
        )

    def ingest_raw_matches(self, full_backfill: bool = False):
        """
        Retrieve ranked match IDs for the tracked player and ingest new data.

        Raw match payloads are downloaded only when they do not already exist
        in raw_matches. Player-match relationships are inserted separately so
        one raw match can be associated with multiple tracked players.

        Args:
            full_backfill:
                If False, stop once previously processed player matches are
                reached. If True, continue through all available match pages.
        """

        logger.info(
            "Starting match ingestion for %s#%s.",
            self.game_name,
            self.tag_line
        )

        # Load existing IDs into sets so membership checks can be performed
        # efficiently while processing Riot match pages.
        existing_match_ids = self.db.get_existing_raw_match_ids()

        existing_player_match_ids = (
            self.db.get_existing_player_match_ids(self.puuid)
        )

        # Riot API pagination state.
        start = 0
        page_size = 25

        # Track how many new raw match payloads are inserted during this run.
        inserted = 0

        while True:

            # Retrieve one page of ranked match IDs for the tracked player.
            match_ids = self.riot_client.get_ranked_match_ids(
                start_=start,
                count_=page_size
            )

            # An empty response means there are no additional matches.
            if not match_ids:
                break

            # Identify matches whose raw JSON payload has not yet been stored.
            new_raw_match_ids = [
                match_id
                for match_id in match_ids
                if match_id not in existing_match_ids
            ]

            # Identify matches that have not yet been associated with
            # the current tracked player.
            new_player_match_ids = [
                match_id
                for match_id in match_ids
                if match_id not in existing_player_match_ids
            ]

            # Log a summary for the current page.
            logger.info("Retrieved: %s", len(match_ids))
            logger.info("New raw matches: %s", len(new_raw_match_ids))
            logger.info(
                "New player relationships: %s",
                len(new_player_match_ids)
            )

            for match_id in match_ids:

                # Download and store the complete match payload only when
                # the match does not already exist in raw_matches.
                if match_id not in existing_match_ids:

                    logger.debug(
                        "Ingesting raw match: %s",
                        match_id
                    )

                    payload = self.riot_client.get_match_data(match_id)

                    self.db.insert_raw_match(
                        match_id=match_id,
                        game_json=payload
                    )

                    # Update the in-memory set so the same match cannot be
                    # treated as new again during this ingestion run.
                    existing_match_ids.add(match_id)
                    inserted += 1

                # Create the player-match relationship independently from the
                # raw match insert. A raw match may already exist because it
                # was previously discovered through another tracked player.
                if match_id not in existing_player_match_ids:

                    self.db.insert_player_match(
                        self.puuid,
                        match_id
                    )

                    # Keep the in-memory relationship state synchronized with
                    # the database writes performed during this run.
                    existing_player_match_ids.add(match_id)

            # During incremental ingestion, stop once an entire page contains
            # no new relationships for this player. Older pages have already
            # been processed.
            if not full_backfill and not new_player_match_ids:

                logger.info(
                    "Reached previously ingested matches for this player."
                )

                break

            # A partial page indicates that Riot has no additional match IDs
            # available after this page.
            if len(match_ids) < page_size:
                break

            # Move the Riot API pagination offset to the next page.
            start += page_size

        # Report the result of the ingestion run.
        if inserted == 0:
            logger.info("No new raw matches found.")
        else:
            logger.info(
                "Successfully inserted %s new raw matches.",
                inserted
            )


if __name__ == "__main__":

    # Configure console and file logging before creating pipeline components.
    setup_logging()

    # Load environment variables such as the Riot API key and database
    # connection credentials from the project's .env file.
    load_dotenv()

    API_KEY = os.getenv("RIOT_API_KEY")

    # Create the Riot API client for the player being ingested.
    client = RiotClient(
        api_key=API_KEY,
        game_name="coolguy",
        tag_line="super"
    )

    # Create the PostgreSQL database client.
    db = PostgresClient()

    # Connect the Riot API and database layers through the ingestion service.
    ingestion = MatchIngestion(
        riot_client=client,
        db=db
    )

    # Perform an incremental ingestion. Set full_backfill=True when the
    # complete available match history should be traversed.
    ingestion.ingest_raw_matches(full_backfill=False)