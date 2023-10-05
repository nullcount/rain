import time
from lnd import Lnd
from base import SendOnchainRequest, PayInvoiceRequest, OpenChannelRequest, CloseChannelRequest
from mempool import BitcoinCore
from config import config
from wos import Wos

config_path = 'test.config.yml'
creds_path = 'test.creds.yml'

def test_bitcoin_lightning_node() -> None:
    alice_creds = config.get_creds(creds_path, 'lnd-alice')
    bob_creds = config.get_creds(creds_path, 'lnd-bob')

    alice = Lnd(creds_path, 'lnd-alice')
    bob = Lnd(creds_path, 'lnd-bob')
    core = BitcoinCore(creds_path)

    # Get onchain address
    alice_address = alice.get_address().unwrap()
    bob_address = bob.get_address().unwrap()

    # Mine some blocks to fund nodes
    core.rpc_request('generatetoaddress', [20, bob_address])
    core.rpc_request('generatetoaddress', [20, alice_address])

    # Get own pubkey
    bob_pub_key = bob.get_pubkey().unwrap()
    alice.get_alias(bob_pub_key)

    # Sign a message
    alice.sign_message("Make it rain")

    # Get confirmed balance
    alice.get_confirmed_balance()
    bob.get_confirmed_balance()

    # Send onchain
    send_onchain_req = SendOnchainRequest(amount_sats=1000, dest_addr=bob_address, vbyte_sats=1)
    alice.send_onchain(send_onchain_req)

    # Get unconfirmed balance
    alice.get_unconfirmed_balance()
    bob.get_unconfirmed_balance()

    # Mine some blocks to confirm onchain send
    core.rpc_request('generatetoaddress', [1, bob_address])
    core.rpc_request('generatetoaddress', [1, alice_address])

    # Get confirmed balance
    alice.get_confirmed_balance()
    bob.get_confirmed_balance()

    # Open channel alice to bob
    open_req = OpenChannelRequest(
        peer_pubkey=bob_pub_key,
        peer_host=bob_creds.grpc_host,
        capacity=1_000_000,
        base_fee=0,
        ppm_fee=100,
        cltv_delta=144,
        min_htlc_sats=1,
        vbyte_sats=2      
    )
    alice.open_channel(open_req)

    # Get pending open channels
    alice.get_pending_open_channels()
    bob.get_pending_open_channels()

    # Mine some blocks to confirm the channel 
    core.rpc_request('generatetoaddress', [6, bob_address])
    core.rpc_request('generatetoaddress', [6, alice_address])

    # Get opened channels
    alice_open_chans = alice.get_opened_channels().unwrap()
    bob_open_chans = bob.get_opened_channels().unwrap()

    # Create an invoice
    bob_invoice = bob.get_invoice(sats=10).unwrap()

    # Decode an invoice
    alice.decode_invoice(bob_invoice)

    # Pay invoice
    pay_req = PayInvoiceRequest(invoice=bob_invoice, fee_limit_sats=10)
    alice.pay_invoice(pay_req)

    # Allow HTLCs to settle
    time.sleep(5)

    # Get opened channels
    alice_open_chans = alice.get_opened_channels().unwrap()
    bob_open_chans = bob.get_opened_channels().unwrap()

    time.sleep(2)

    # Close channels
    for chan in alice_open_chans:
        close_req = CloseChannelRequest(channel_point=chan.channel_point, vbyte_sats=1, is_force=False)
        alice.close_channel(close_req)

    # Close channels
    for chan in bob_open_chans:
        close_req = CloseChannelRequest(channel_point=chan.channel_point, vbyte_sats=1, is_force=False)
        bob.close_channel(close_req)

    # Mine some blocks to confirm close channels
    core.rpc_request('generatetoaddress', [20, bob_address])
    core.rpc_request('generatetoaddress', [20, alice_address])

def test_trusted_swap_service() -> None:
    swap = Wos(creds_path)
    swap.get_address()
    balance = swap.get_balance().unwrap()
    fee = swap.get_onchain_fee(sats=balance).unwrap()
    #swap.get_invoice(13_041_904)
    #swap.pay_invoice(invoice="adsf")
    # TODO test send_onchain
    #swap.send_onchain(sats=balance, fee=fee)
    swap.pay_invoice(invoice="lnbc10u1pj3u23qpp5paav59ldev4qzf0hw20l7vvy7sj4rprlr3mr0dl57z3l3vme9qdsdp8fe5kxetgv9eksgzyv4cx7umfwssyjmnkda5kxegcqzysxqr8pqsp5qq3mapdksuqrmfx4smdpe4duw35e5casd3y8zy7ph7eq5hz7d27q9qyyssqrfedel2cygt4r834j3emgqxhhdatllzfdq0vrc7lwxcqvgf5mknna0dz0ulwm738hzh58hjaejlgpjud3srgdn8rvek0kqv000m3a2cqlt29ps")

def main() -> None:
   #test_bitcoin_lightning_node()
    test_trusted_swap_service()

if __name__ == "__main__":
    main()
