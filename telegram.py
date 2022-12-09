import requests
import time
from report import Report
from config import Config

CONFIG = Config('listen.config.example').config


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
        self.report = Report(CONFIG['REPORT'], node, logger)
        self.daily_report = tg_config['daily_report']
        self.daily_report_hour = int(tg_config['daily_report_hour'])
        self.daily_report_min = int(tg_config['daily_report_min'])
        actions = tg_config['actions'].split(' ')
        self.actions = {
                "invoice": {
                    "permission": "invoice" in actions,
                    "parse_args": lambda msg: (msg.split(' ')[1], " ".join(msg.split(' ')[1:])),
                    "action": lambda args: self.tg.send_message(f"{self.node.add_lightning_invoice(args[0], args[1])}")
                },
                "report": {
                    "permission": "report" in actions,
                    "action": self.report.send_report
                }
        }

    def mainLoop(self):
        while True:
            if self.daily_report:
                self.daily_report_check_send()
            self.handle_updates()
            time.sleep(5)

    def daily_report_check_send(self):
        current_time = time.localtime()
        if current_time.tm_hour == self.daily_report_hour and \
                current_time.tm_min == self.daily_report_min:
            self.report.send_report()

    def handle_updates(self):
        updates = self.tg.get_updates()
        for update in updates:
            msg = update['message']['text']
            self.tg.ack_update(update['update_id'])
            for action in self.actions:
                if msg.startswith(f"/{action}"):
                    if self.actions[action]['permission']:
                        if self.actions[action]['parse_args']:
                            self.actions[action]['action'](self.actions[action]['parse_args'])
                        else:
                            self.actions[action]['action']()
                    else:
                        self.tg.send_message(f"/{action} is not an allowed action")
