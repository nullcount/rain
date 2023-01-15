class SwapMethod:
    def get_onchain_address(self):
        # returns address string
        raise NotImplementedError

    def send_onchain(self):
        # sends entire account balance to saved onchain address
        raise NotImplementedError

    def get_account_balance(self):
        # returns total balance in sats
        raise NotImplementedError

    def pay_invoice(self, inv):
        # attempts to pay the invoice using account balance
        raise NotImplementedError

    def get_lightning_invoice(self):
        # returns bolt11 invoice string
        raise NotImplementedError

    def estimate_onchain_fee(self):
        # returns the total fee in satoshis
        raise NotImplementedError
