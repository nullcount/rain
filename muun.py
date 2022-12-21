

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
            "get_pending_send_sats": lambda amt : f"muun send of {amt} sats",
            "get_account_balance": lambda sats: f"muun wallet balance: {sats} sats",
            "send_to_acct": lambda sats: f"sending {int(sats)} sats into muun wallet",
            "get_lightning_invoice": lambda sats, invoice: f"muun wallet request for {sats} sats invoice: {invoice}"
        }

    @staticmethod
    def should_pay_invoice(invoice):
        for hint in lnd.decode_invoice(invoice).route_hints:
            if hint.fee_base_msat > 1000:
                return False
            elif hint.fee_proportional_millionths > 1500:
                return False
        return True

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
