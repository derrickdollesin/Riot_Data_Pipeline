from unittest.mock import MagicMock

from src.ingestion.match_ingestion import MatchIngestion


def test_ingests_only_new_raw_matches():
    """
    Verify that only matches missing from raw_matches are fetched
    from Riot and inserted into the database.
    """

    # Mock external dependencies so the test does not call the real
    # Riot API or PostgreSQL database.
    riot_client = MagicMock()
    db = MagicMock()

    # Simulate the player information normally provided by RiotClient.
    riot_client.puuid = "test-puuid"
    riot_client.game_name = "TestPlayer"
    riot_client.tag_line = "NA1"

    # Simulate Riot returning three ranked matches for the player.
    riot_client.get_ranked_match_ids.return_value = [
        "NA1_100",
        "NA1_101",
        "NA1_102"
    ]

    # Simulate the payload returned when the new match is requested.
    riot_client.get_match_data.return_value = {
        "metadata": {"matchId": "NA1_102"}
    }

    # MATCH_100 and MATCH_101 already exist in raw_matches.
    # Therefore, only MATCH_102 should need to be downloaded.
    db.get_existing_raw_match_ids.return_value = {
        "NA1_100",
        "NA1_101"
    }

    # The player is already linked to MATCH_100 and MATCH_101.
    db.get_existing_player_match_ids.return_value = {
        "NA1_100",
        "NA1_101"
    }

    # Create the ingestion service using the mocked dependencies.
    ingestion = MatchIngestion(
        riot_client=riot_client,
        db=db
    )

    ingestion.ingest_raw_matches()

    # Verify that Riot was queried only for the missing raw match.
    riot_client.get_match_data.assert_called_once_with(
        "NA1_102"
    )

    # Verify that the new match payload was inserted correctly.
    db.insert_raw_match.assert_called_once_with(
        match_id="NA1_102",
        game_json={"metadata": {"matchId": "NA1_102"}}
    )


def test_links_existing_raw_match_to_player():
    """
    Verify that an existing raw match can be linked to a player
    without downloading or inserting the raw match again.
    """

    riot_client = MagicMock()
    db = MagicMock()

    # Simulate player information.
    riot_client.puuid = "test-puuid"
    riot_client.game_name = "TestPlayer"
    riot_client.tag_line = "NA1"

    # Riot reports three matches belonging to the player.
    riot_client.get_ranked_match_ids.return_value = [
        "NA1_100",
        "NA1_101",
        "NA1_102"
    ]

    # All three matches already exist globally in raw_matches.
    db.get_existing_raw_match_ids.return_value = {
        "NA1_100",
        "NA1_101",
        "NA1_102"
    }

    # The player is only linked to the first two matches.
    db.get_existing_player_match_ids.return_value = {
        "NA1_100",
        "NA1_101"
    }

    ingestion = MatchIngestion(
        riot_client=riot_client,
        db=db
    )

    ingestion.ingest_raw_matches()

    # Since all raw matches already exist, Riot should not be queried
    # for match payloads and no raw matches should be inserted.
    riot_client.get_match_data.assert_not_called()
    db.insert_raw_match.assert_not_called()

    # The missing player-to-match relationship should still be created.
    db.insert_player_match.assert_called_once_with(
        "test-puuid",
        "NA1_102"
    )


def test_no_new_matches():
    """
    Verify that no database writes or Riot match-data requests occur
    when every returned match has already been fully ingested.
    """

    riot_client = MagicMock()
    db = MagicMock()

    riot_client.puuid = "test-puuid"
    riot_client.game_name = "TestPlayer"
    riot_client.tag_line = "NA1"

    riot_client.get_ranked_match_ids.return_value = [
        "MATCH_1",
        "MATCH_2",
        "MATCH_3"
    ]

    # All returned matches already exist in raw_matches.
    db.get_existing_raw_match_ids.return_value = {
        "MATCH_1",
        "MATCH_2",
        "MATCH_3"
    }

    # All returned matches are also already associated with this player.
    db.get_existing_player_match_ids.return_value = {
        "MATCH_1",
        "MATCH_2",
        "MATCH_3"
    }

    ingestion = MatchIngestion(
        riot_client=riot_client,
        db=db
    )

    ingestion.ingest_raw_matches()

    # Nothing new exists, so no additional API requests or database
    # inserts should occur.
    riot_client.get_match_data.assert_not_called()
    db.insert_raw_match.assert_not_called()
    db.insert_player_match.assert_not_called()


def test_all_matches_are_new():
    """
    Verify that every match is downloaded, inserted, and linked
    when neither raw matches nor player relationships exist.
    """

    riot_client = MagicMock()
    db = MagicMock()

    riot_client.puuid = "test-puuid"
    riot_client.game_name = "TestPlayer"
    riot_client.tag_line = "NA1"

    # Simulate three newly discovered Riot matches.
    riot_client.get_ranked_match_ids.return_value = [
        "MATCH_1",
        "MATCH_2",
        "MATCH_3"
    ]

    # Return a different payload for each call to get_match_data().
    riot_client.get_match_data.side_effect = [
        {"match": "MATCH_1"},
        {"match": "MATCH_2"},
        {"match": "MATCH_3"}
    ]

    # Empty sets simulate a player/database with no existing matches.
    db.get_existing_raw_match_ids.return_value = set()
    db.get_existing_player_match_ids.return_value = set()

    ingestion = MatchIngestion(
        riot_client=riot_client,
        db=db
    )

    ingestion.ingest_raw_matches()

    # Each of the three matches should be downloaded once.
    assert riot_client.get_match_data.call_count == 3

    # Each raw match should be inserted into raw_matches.
    assert db.insert_raw_match.call_count == 3

    # Each match should also be associated with the tracked player.
    assert db.insert_player_match.call_count == 3


def test_pagination():
    """
    Verify that ingestion requests subsequent pages when Riot returns
    a full page of match IDs and uses the correct pagination offset.
    """

    riot_client = MagicMock()
    db = MagicMock()

    riot_client.puuid = "test-puuid"
    riot_client.game_name = "TestPlayer"
    riot_client.tag_line = "NA1"

    # MatchIngestion currently uses a page size of 25.
    # A full first page should cause another API request.
    first_page = [
        f"MATCH_{i}"
        for i in range(1, 26)
    ]

    # A partial second page indicates that there are no more pages.
    second_page = [
        "MATCH_26",
        "MATCH_27"
    ]

    # First get_ranked_match_ids() call returns first_page;
    # the second call returns second_page.
    riot_client.get_ranked_match_ids.side_effect = [
        first_page,
        second_page
    ]

    # Dynamically generate a payload corresponding to each requested match.
    riot_client.get_match_data.side_effect = (
        lambda match_id: {"match": match_id}
    )

    # Treat every returned match as new.
    db.get_existing_raw_match_ids.return_value = set()
    db.get_existing_player_match_ids.return_value = set()

    ingestion = MatchIngestion(
        riot_client=riot_client,
        db=db
    )

    ingestion.ingest_raw_matches()

    # Riot should be queried for exactly two pages.
    assert riot_client.get_ranked_match_ids.call_count == 2

    # Verify the first page starts at offset 0.
    riot_client.get_ranked_match_ids.assert_any_call(
        start_=0,
        count_=25
    )

    # Verify the second page starts immediately after the first 25 matches.
    riot_client.get_ranked_match_ids.assert_any_call(
        start_=25,
        count_=25
    )

    # 25 matches from page one + 2 matches from page two = 27.
    assert riot_client.get_match_data.call_count == 27
    assert db.insert_raw_match.call_count == 27
    assert db.insert_player_match.call_count == 27