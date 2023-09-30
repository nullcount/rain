import requests
from base import AdminNotifyService
from const import TELEGRAM_API_URL
from config import config
from typing import Any

class Telegram(AdminNotifyService):
    """
    Use telegram bot to notify of events
        or seek approval for actions
    """
    def __init__(self, creds_path: str) -> None:
        self.creds = config.get_creds(creds_path, 'telegram')
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
