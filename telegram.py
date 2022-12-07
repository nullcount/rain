import requests
import time


class Telegram:
    def __init__(self, TG_INFO, logger):
        self.api_token = TG_INFO['api_token']
        self.chat_id = TG_INFO['chat_id']
        self.log = logger
        self.last_update_id = None

    def telegram_request(self, endpoint, params):
        url = f"https://api.telegram.org/bot{self.api_token}/{endpoint}{params}"
        res = requests.get(url).json()
        if res['ok']:
            return res['result']
        self.log.warning(f"Telegram failed !!! {endpoint}{params}")

    def send_message(self, message):
        return self.telegram_request('sendMessage', f'?chat_id={self.chat_id}&text={message}&parse_mode=Markdown')

    def get_updates(self):
        return self.telegram_request('getUpdates', f'?chat_id={self.chat_id}&offset={self.last_update_id}')

    def ack_update(self, update_id):
        self.last_update_id = int(update_id) + 1

class TelegramListener:
    def __init__(self, tg_config, node, logger):
        self.tg = logger.notify_connector
        self.node = node

    def mainLoop(self):
        while True:
            updates = self.tg.get_updates()
            for update in updates:
                msg = update['message']['text']
                self.tg.ack_update(update['update_id'])
                if msg.startswith("/"):
                    if msg.startswith("/invoice"):
                        words = msg.split(' ')
                        amt = words[1]
                        if amt.isnumeric():
                            memo = " ".join(words[1:])
                            inv = self.node.add_lightning_invoice(int(amt), memo)
                            self.tg.send_message(f"{inv.payment_request}")
                        else: 
                            self.tg.send_message("usage: /invoice <sat_amount> <memo>")
                else:
                    self.tg.send_message(msg)
            time.sleep(5)




            

