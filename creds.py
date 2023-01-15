class KrakenCreds:
    def __init__(self, creds: dict):
        self.api_key = creds['api_key']
        self.api_secret = creds['api_secret']
        self.funding_key = creds['funding_key']


class MuunCreds:
    def __init__(self, creds: dict):
        self.device_name = creds['device_name']
        self.widthdraw_address = creds['widthdraw_address']


class NicehashCreds:
    def __init__(self, creds: dict):
        self.api_key = creds['api_key']
        self.api_secret = creds['api_secret']
        self.org_id = creds['org_id']
        self.funding_key = creds['funding_key']


class TelegramCreds:
    def __init__(self, api_token: str, chat_id: str):
        self.api_token = api_token
        self.chat_id = chat_id
