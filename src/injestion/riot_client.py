import os
import sys
import time 
import requests 

root_path = os.path.abspath(os.path.join(os.getcwd(), '..'))
if root_path not in sys.path:
    sys.path.append(root_path)

from src.utils.rate_limiter import RateLimiter

class RiotClient:

    ### NEED TO CHANGE TO PERSONAL API TOKEN WHEN PUBLIC

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }

    def __init__(self, api_key:str, game_name:str, tag_line:str):

        self.rate_limiter = RateLimiter([
            (20, 1),
            (100, 120)
        ])

        self.api_key = api_key
        self.game_name = game_name
        self.tag_line = tag_line

        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        url = (
            f'https://americas.api.riotgames.com/riot/account/v1/accounts/'
            f'by-riot-id/{self.game_name}/{self.tag_line}'
        ) 

        account = self.get_json(url)

        self.puuid = account['puuid']


    def get_json(self, url, params=None):

        self.rate_limiter.acquire()

        params = params.copy() if params else {}

        params["api_key"] = self.api_key

        response = self.session.get(
            url,
            headers=self.HEADERS,
            params=params, 
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def get_ranked_match_ids(
            self, 
            start_time=1623801600,     # date of beginnig dev data
            end_time=None, # current time
            game_type='ranked', 
            start_=0,                  # index 0 is last game played
            count_=20                  # 20 entries in response
    ):
        if end_time is None:
            end_time = int(time.time())

        url = (
            "https://americas.api.riotgames.com/lol/match/v5/matches/"
            f"by-puuid/{self.puuid}/ids"
        )

        params = {
            'startTime':start_time, 
            'endTime':end_time, 
            'gameType':game_type, 
            'start':start_, 
            'count':count_
        }

        return self.get_json(url=url, params=params)

    def get_match_data(self, match_id):
        url = (
            'https://americas.api.riotgames.com/lol/match/v5/matches/'
            f'{match_id}'
        )

        return self.get_json(url)