import requests
from base import AdminChatBot
from const import TELEGRAM_API_URL
from config import get_creds

class Telegram(AdminChatBot):
    def __init__(self):
        self.creds = get_creds('telegram')
        self.last_update_id = None

    def telegram_request(self, endpoint, params):
        url = f"{TELEGRAM_API_URL}bot{self.creds.api_token}/{endpoint}{params}"
        res = requests.get(url).json()
        if res['ok']:
            return res['result']
        # TODO self.log.warning(f"Telegram failed !!! {endpoint}{params}")

    def send_message(self, message):
        return self.telegram_request('sendMessage', f'?chat_id={self.creds.chat_id}&text={message}&parse_mode=Markdown')

    def get_updates(self):
        return self.telegram_request('getUpdates', f'?chat_id={self.creds.chat_id}&offset={self.last_update_id}')

    def ack_update(self, update_id):
        self.last_update_id = int(update_id) + 1

    # TODO get confirm from permissioned user in chat i.e. y/N then do callback
