class OkCreds:
    def __init__(self, creds: dict):
        self.loop_out_address = creds['loop_out_address']
        self.api_token = creds['api_token']
        self.api_secret = creds['api_secret']
        self.api_passphrase = creds['api_passphrase']


class WosCreds:
    def __init__(self, creds: dict):
        self.api_secret = creds['api_secret']
        self.api_token = creds['api_token']
        self.btc_deposit_address = creds['btc_deposit_address']
        self.lightning_address = creds['lightning_address']
        self.loop_out_address = creds['loop_out_address']


class KrakenCreds:
    def __init__(self, creds: dict):
        self.username = creds["username"]
        self.password = creds["password"]
        self.api_key = creds['api_key']
        self.api_secret = creds['api_secret']
        self.funding_key = creds['funding_key']
        self.otp_secret = creds['otp_secret']


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
