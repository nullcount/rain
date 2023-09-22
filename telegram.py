import requests
from base import AdminChatService
from const import TELEGRAM_API_URL
from config import get_creds, log
from typing import Any

class Telegram(AdminChatService):
    def __init__(self) -> None:
        self.creds = get_creds('telegram')
        self.last_update_id: int = 0

    def telegram_request(self, endpoint: str, params: str) -> dict[Any, Any] | None:
        url = f"{TELEGRAM_API_URL}bot{self.creds.api_token}/{endpoint}{params}"
        res = requests.get(url).json()
        if res['ok']:
            resp: dict[Any, Any] = res['result']
            return resp
        return None
        # TODO self.log.warning(f"Telegram failed !!! {endpoint}{params}")

    def send_message(self, message: str) -> dict[Any, Any] | None:
        return self.telegram_request('sendMessage', f'?chat_id={self.creds.chat_id}&text={message}&parse_mode=Markdown')
    
    def get_updates(self) -> dict[Any, Any] | None:
        return self.telegram_request('getUpdates', f'?chat_id={self.creds.chat_id}&offset={self.last_update_id}')

    def ack_update(self, update_id: int) -> None:
        self.last_update_id = int(update_id) + 1

    # TODO get confirm from permissioned user in chat i.e. y/N then do callback
