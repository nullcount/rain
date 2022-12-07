import requests
import time


class Telegram:
    def __init__(self, TG_INFO, logger):
        self.api_token = TG_INFO['api_token']
        self.chat_id = TG_INFO['chat_id']
        self.log = logger
        self.last_update_id = None

    def send_message(self, message):
        url = f"https://api.telegram.org/bot{self.api_token}/sendMessage?chat_id={self.chat_id}&text={message}"
        res = requests.get(url).json()
        if res['ok']:
            return res
        self.log.warning("Telegram failed to send message")
        self.log.debug(f"message: {message}")
        self.log.debug(f"response: {res}")

    def get_updates(self):
        updates = requests.get(f"https://api.telegram.org/bot{self.api_token}/getUpdates?chat_id={self.chat_id}&offset={self.last_update_id}")
        return updates

    def handle_message(message):
        if message.text.startswith("/invoice"):
            cmd, amount, memo = message.text.split(" ")


class TelegramListener:
    def __init__(self, tg_config, node, logger):
        self.tg = logger.notify_connector
        self.node = node

    def mainLoop(self):
        while True:
            updates = self.tg.get_updates()
            for update in updates:
                cmd, amount, memo = update['message'].split(' ')
                self.send_message(f"{cmd} {amount} {memo}")
            time.sleep(5)




            

