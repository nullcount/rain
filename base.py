class TrustedSwapService:
    """
    Extend with exchange/wallet APIs 
        to programatically give trusted nodes your sats
        and to automate widthdraws back to your node
    """
    def get_address(self):
        # returns onchain address string to deposit into the third-party wallet/account balance
        raise NotImplementedError

    def send_onchain(self, sats: int, fee: int):
        # initiate a widthdrawl request for number of `sats` sent with `fee` sats/vbyte
        # not every api supports user-suggested feerates so `fee` may be unused
        print([sats, fee])
        raise NotImplementedError

    def get_balance(self):
        # returns total wallet/account balance in sats
        raise NotImplementedError

    def pay_invoice(self, invoice: str):
        # attempts to pay the `invoice` using account balance
        print(invoice)
        raise NotImplementedError

    def get_invoice(self, sats: int):
        # returns bolt11 invoice string requesting number of `sats`
        print(sats)
        raise NotImplementedError

    def estimate_onchain_fee(self, sats: int):
        # returns the total fee in satoshis to widthdraw `sats` from balance
        print(sats)
        raise NotImplementedError
