from ppadb.client import Client as AdbClient
from time import sleep
from bs4 import BeautifulSoup as bs


def parse_bounds(bounds_str):
    return [[int(x) for x in point.split(",")] for point in bounds_str[1:-1].split("][")]


def get_midpoint(bounds):
    return [(c1 + c2) / 2 for c1, c2 in zip(*bounds)]


class Muun:
    def __init__(self, CONFIG, log):
        self.log = log
        self.key = CONFIG['api_key']
        self.secret = CONFIG['api_secret']
        self.organisation_id = CONFIG['org_id']
        self.funding_key = CONFIG['funding_key']
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"muun deposit address: {addr}",
            "send_onchain": lambda sats: f"muun initiated {sats} sat widthdrawl",
            "get_onchain_fee": lambda fee, sats: f"muun fee: {fee} sats widthdraw amount: {sats} sats",
            "get_pending_send_sats": lambda amt: f"muun send of {amt} sats",
            "get_account_balance": lambda sats: f"muun wallet balance: {sats} sats",
            "send_to_acct": lambda sats: f"sending {int(sats)} sats into muun wallet",
            "get_lightning_invoice": lambda sats, invoice: f"muun wallet request for {sats} sats invoice: {invoice}"
        }
        # connect to self.device
        client = AdbClient()
        # self.devices = client.devices()

        # self.device = client.device("R58M47ZGS2Z")
        self.device = client.device("emulator-5554")

    def muun_request(self):
        return

    def check_errors(self, response, payload, endpoint):
        return

    def get_onchain_address(self):
        return

    def send_onchain(self, sats):
        return

    def get_onchain_fee(self, sats):
        return

    def get_pending_send_sats(self):
        return

    def get_recent_sends(self):
        return

    def get_account_balance(self):
        return

    def pay_invoice(self, invoice_code):
        return

    def send_to_acct(self, sats, node):
        return

    def get_lightning_invoice(self, sats):
        return

    def get_screen_layout(self):
        xml_dump = self.device.shell(
            """uiautomator dump /dev/tty | awk '{gsub("UI hierchary dumped to: /dev/tty", "");print}'""")
        # print(xml_dump)
        soup_obj = bs(xml_dump, features="xml")
        return soup_obj

    def tap(self, resource_id=None, content_desc=None):
        screen = self.get_screen_layout(self.device)
        if resource_id:
            obj = screen.find("node", {"resource-id": resource_id})
        elif content_desc:
            obj = screen.find("node", {"content-desc": content_desc})
        bounds = parse_bounds(obj["bounds"])
        x, y = get_midpoint(bounds)
        self.device.shell(f"input tap {x} {y}")

    def delete_wallet(self):
        print("Deleting wallet...")
        # click settings
        self.tap("io.muun.apollo:id/settings_fragment")

        # click delete wallet
        self.tap("io.muun.apollo:id/log_out_text_view")

        # confirm deletion
        self.tap("io.muun.apollo:id/positive_button")

    def get_balance(self):
        screen = self.get_screen_layout()
        balance_obj = screen.find("node", {"resource-id": "io.muun.apollo:id/balance_main_currency_amount"})
        balance = float(balance_obj["text"])
        return balance

    def get_invoice(self):
        # click receive
        self.tap("io.muun.apollo:id/muun_button_button")
        # click lightning
        self.tap(content_desc="LIGHTNING")

        # get invoice
        screen = self.get_screen_layout()
        invoice_obj = screen.find("node", {"resource-id": "io.muun.apollo:id/show_qr_content"})
        bolt11 = invoice_obj["text"]
        return bolt11

    def close_app(self):
        self.device.shell("input keyevent KEYCODE_APP_SWITCH")
        sleep(1)
        self.device.shell("input keyevent 20")
        sleep(1)
        self.device.shell("input keyevent DEL")

    def restart_app(self):
        print(self.device.shell("am force-stop io.muun.apollo"))
        print(self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1"))

    def create_wallet(self):
        screen_obj = self.get_screen_layout()
        create_wallet_btn = screen_obj.find("node", {"resource-id": "io.muun.apollo:id/signup_start"})
        if create_wallet_btn:
            print("Creating wallet....")
            self.tap("io.muun.apollo:id/signup_start")
            sleep(1)
            print("Doing a trick so we don't have to make a pin...")
            self.close_app()
            sleep(1)
            print(self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1"))
            return True
        else:
            print("Wallet already created...")
            return False
