class SwapMethod:
    def get_onchain_address(self):
        # returns address string
        raise NotImplementedError

    def send_onchain(self, sats: int, fee: int):
        # sends entire account balance to saved onchain address
        raise NotImplementedError

    def get_account_balance(self):
        # returns total balance in sats
        raise NotImplementedError

    def pay_invoice(self, invoice: str):
        # attempts to pay the invoice using account balance
        raise NotImplementedError

    def get_lightning_invoice(self, sats: int):
        # returns bolt11 invoice string
        raise NotImplementedError

    def estimate_onchain_fee(self, sats: int):
        # returns the total fee in satoshis
        raise NotImplementedError
