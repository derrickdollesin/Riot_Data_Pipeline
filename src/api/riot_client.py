import time
import random
import logging
import requests

from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class RiotClient:
    """
    Client for interacting with Riot Games API endpoints.

    Handles API authentication, request rate limiting, session management,
    account lookup, and Match-V5 requests.
    """

    # NOTE: Replace the development API token with a personal/production
    # API token before publishing or deploying the application.
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }

    def __init__(self, api_key: str, game_name: str, tag_line: str):
        """
        Initialize the Riot API client and retrieve the player's PUUID.

        Args:
            api_key: Riot Games API key used to authenticate requests.
            game_name: Player's Riot ID game name.
            tag_line: Player's Riot ID tag line.
        """

        # Riot personal API rate limits:
        #   - 20 requests per 1 second
        #   - 100 requests per 120 seconds
        self.rate_limiter = RateLimiter([
            (20, 1),
            (100, 120)
        ])

        self.api_key = api_key
        self.game_name = game_name
        self.tag_line = tag_line

        # Reuse a persistent HTTP session across requests.
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        # Retrieve account information using the player's Riot ID.
        url = (
            f'https://americas.api.riotgames.com/riot/account/v1/accounts/'
            f'by-riot-id/{self.game_name}/{self.tag_line}'
        )

        account = self.get_json(url)

        # Store the PUUID for subsequent player-specific API requests.
        self.puuid = account['puuid']

    def get_json(self, url, params=None, max_retries=3):
        """
        Send a rate-limited GET request and return the JSON response.

        Retries requests that fail due to Riot rate limiting (429)
        or temporary server errors (5xx).

        Args:
            url: Riot API endpoint.
            params: Optional query parameters for the request.
            max_retries: Maximum number of retry attempts.

        Returns:
            Parsed JSON response from the Riot API.
        """

        # Copy parameters once so retries use the same request parameters.
        params = params.copy() if params else {}
        params["api_key"] = self.api_key

        for attempt in range(max_retries + 1):

            # Every retry is another API request, so it must also pass
            # through the local rate limiter.
            self.rate_limiter.acquire()

            try:
                response = self.session.get(
                    url,
                    headers=self.HEADERS,
                    params=params,
                    timeout=30
                )

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError
            ) as e:
                if attempt == max_retries:
                    raise 

                wait_time = (
                    (2 ** attempt) + 
                    random.uniform(a=1, b=9) * 0.1
                )

                logger.warning(
                    "Request failed: %s. Retrying in %.1f seconds...",
                    e,
                    wait_time
                )

                time.sleep(wait_time)

                continue

            # Riot rate limit exceeded.
            if response.status_code == 429:

                if attempt == max_retries:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")

                if retry_after is not None:
                    wait_time = float(retry_after)
                else:
                    wait_time = 10

                logger.warning(
                    f"Rate limited by Riot. "
                    f"Retrying in {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                continue

            # Temporary Riot/server failure.
            if 500 <= response.status_code < 600:

                if attempt == max_retries:
                    response.raise_for_status()

                wait_time = (
                    (2 ** attempt) + 
                    random.uniform(a=1, b=9) * 0.1
                )

                logger.warning(
                    "Server error %s. Retrying in %.1f seconds...",
                    response.status_code,
                    wait_time
                )

                time.sleep(wait_time)
                continue

            # Don't retry other errors such as 400, 401, 403, etc.
            response.raise_for_status()

            return response.json()

    def get_ranked_match_ids(
            self,
            start_time=1623801600,  # Beginning of available development data
            end_time=None,         # Defaults to the current Unix timestamp
            type='ranked',
            start_=0,              # Index 0 represents the most recent match
            count_=20              # Maximum number of match IDs to return
    ):
        """
        Retrieve ranked match IDs associated with the client's PUUID.

        Args:
            start_time: Beginning of the match search period as a Unix timestamp.
            end_time: End of the match search period as a Unix timestamp.
            game_type: Match type used to filter results.
            start_: Starting index for pagination.
            count_: Number of match IDs to request.

        Returns:
            JSON response containing matching Riot match IDs.
        """

        # Use the current Unix timestamp when no end time is provided.
        if end_time is None:
            end_time = int(time.time())

        url = (
            "https://americas.api.riotgames.com/lol/match/v5/matches/"
            f"by-puuid/{self.puuid}/ids"
        )

        params = {
            'startTime': start_time,
            'endTime': end_time,
            'gameType': type,
            'start': start_,
            'count': count_
        }

        return self.get_json(url=url, params=params)

    def get_match_data(self, match_id):
        """
        Retrieve complete match data for a specific Riot match ID.

        Args:
            match_id: Unique Riot match identifier.

        Returns:
            Parsed JSON match data.
        """

        url = (
            'https://americas.api.riotgames.com/lol/match/v5/matches/'
            f'{match_id}'
        )

        return self.get_json(url)