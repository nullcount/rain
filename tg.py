import requests
from config import Config

CONFIG = Config().config
TOKEN = CONFIG["TG_INFO"]["api_token"]


def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    print(requests.get(url).json())
    chat_id = requests.get(url).json()["result"][0]['message']["chat"]["id"]
    return chat_id


# make sure to send a message to your bot first
def send_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    print(requests.get(url).json())  # this sends the message


chat_id = get_chat_id()
send_message(token=TOKEN, chat_id=chat_id, message=f"hello from your telegram bot, our chat id is: {chat_id}")
