from ppadb.client import Client as AdbClient
from time import sleep
from bs4 import BeautifulSoup as bs
from config import LISTEN_LOG, CREDS


def parse_bounds(bounds_str):
    return [[int(x) for x in point.split(",")] for point in bounds_str[1:-1].split("][")]


def get_midpoint(bounds):
    return [(c1 + c2) / 2 for c1, c2 in zip(*bounds)]


class Muun:
    def __init__(self, MUUN_CRED, log):
        self.log = log
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
        self.device = client.device(MUUN_CRED["device_name"])

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

    def tap(self, param_dict):
        screen = self.get_screen_layout()
        obj = screen.find("node", param_dict)
        bounds = parse_bounds(obj["bounds"])
        x, y = get_midpoint(bounds)
        self.device.shell(f"input tap {x} {y}")

    def delete_wallet(self):
        self.log.info("Deleting wallet...")
        # click settings
        self.tap(element_dict["settings"])

        # click delete wallet
        self.tap(element_dict["delete-wallet"])

        # confirm deletion
        self.tap(element_dict["confirm-btn"])

    def get_balance(self):
        screen = self.get_screen_layout()
        balance_obj = screen.find("node", {"resource-id": "io.muun.apollo:id/balance_main_currency_amount"})
        balance = float(balance_obj["text"])
        return balance

    def get_invoice(self):
        # click receive
        self.tap(element_dict["receive-btn"])
        # click lightning
        self.tap(element_dict["lightning-tab"])

        # get invoice
        screen = self.get_screen_layout()
        invoice_obj = screen.find("node", element_dict["qr-code"])
        bolt11 = invoice_obj["text"]
        return bolt11

    def close_app(self):
        self.device.shell("input keyevent KEYCODE_APP_SWITCH")
        sleep(1)
        self.device.shell("input keyevent 20")
        sleep(1)
        self.device.shell("input keyevent DEL")

    def restart_app(self):
        self.device.shell("am force-stop io.muun.apollo")
        self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1")

    def create_wallet(self):
        screen_obj = self.get_screen_layout()
        create_wallet_btn = screen_obj.find("node", {"resource-id": "io.muun.apollo:id/signup_start"})
        if create_wallet_btn:
            self.log.info("Creating wallet....")
            self.tap(element_dict["create-wallet"])
            sleep(1)
            self.log.info("Doing a trick so we don't have to make a pin...")
            self.close_app()
            sleep(1)
            self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1")
            return True
        else:
            self.log.info("Wallet already created...")
            return False

    def get_backup_key(self):
        """
        Expecting to be on the main screen of muun wallet
        """
        self.tap(element_dict["security-tab"])
        screen = self.get_screen_layout()
        backup_steps = screen.findAll("node", element_dict["backup-step"])
        if screen.find("node", element_dict["email-skipped"]):
            pass
        else:
            self.tap({"text": backup_steps[0]["text"], **element_dict["backup-step"]})
            self.tap(element_dict["no-email"])
            self.tap(element_dict["confirm-btn"])
        self.tap({"text": backup_steps[1]["text"], **element_dict["backup-step"]})
        self.tap(element_dict["start-backup"])

        screen = self.get_screen_layout()
        key = " ".join([x["text"] for x in screen.findAll("node", element_dict["backup-chunk"])])
        self.log.info(key)
        return key


def main():
    wallet = Muun(CREDS["MUUN"], LISTEN_LOG)
    wallet.restart_app()
    wallet.get_backup_key()


element_dict = {
    "balance": {"resource-id": "io.muun.apollo:id/balance_main_currency_amount"},
    "settings": {"resource-id": "io.muun.apollo:id/settings_fragment"},
    "delete-wallet": {"resource-id": "io.muun.apollo:id/log_out_text_view"},
    "confirm-btn": {"resource-id": "io.muun.apollo:id/positive_button"},
    "create-wallet": {"resource-id": "io.muun.apollo:id/signup_start"},
    "qr-code": {"resource-id": "io.muun.apollo:id/show_qr_content"},
    "receive-btn": {"resource-id": "io.muun.apollo:id/muun_button_button", "text": "RECEIVE"},
    "lightning-tab": {"content-desc": "LIGHTNING"},
    "wallet-backup": {"resource-id": "io.muun.apollo:id/muun_text_input_edit_text"},
    "security-tab": {"resource-id": "io.muun.apollo:id/security_center_fragment", },
    "backup-step": {"resource-id": "io.muun.apollo:id/title"},
    "email-skipped": {"resource-id": "io.muun.apollo:id/tag_email_skipped", "text": "Skipped"},
    "no-email": {"content-desc": "I don't want to use my email"},
    "start-backup": {"resource-id": "io.muun.apollo:id/muun_button_button", "text": "START"},
    "backup-chunk": {"resource-id": "io.muun.apollo:id/muun_text_input_edit_text"}

}
if __name__ == '__main__':
    main()
