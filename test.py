from lnd import Lnd
from base import SendOnchainRequest, PayInvoiceRequest, OpenChannelRequest, CloseChannelRequest

config_path = 'test.config.yml'
creds_path = 'test.creds.yml'

node = Lnd(creds_path)

# Get the alias of the node
pub_key = "02c7580426685e367d804fa227d5510e4b7d89fb5ff6e09ecc6666f233e4c3fa1b"
alias = node.get_alias(pub_key).unwrap()

# Sign a message
signed = node.sign_message("yo mama")

# Decode an invoice
invoice = "lnbcrt690n1pj3s52jpp5ljxs3zy258pgnnsz8zsq9c8epjfjvup299p94ly4v9wm0xwj2xhsdqqcqzpgxqyz5vqsp5nfgmfl6p7zuxdup0jejapaclhunttzxd6dx8kq4pkshlgsfkhnvs9qyyssqx5nupg8mh7tag94xm63ks3z54g579ye5ld2jp5sd802kvsrzg5lpwxy2822ppz555fda3samap7qpy75srquyepkk2a40u50ymguq4cqwpa3qd"
decoded = node.decode_invoice(invoice)

# Get confirmed balance
confirmed = node.get_confirmed_balance()

# Get unconfirmed balance
unconfirmed = node.get_unconfirmed_balance()

# Get onchain address
addr = node.get_address()

# Send onchain
#send_onchain_req = SendOnchainRequest(amount_sats=1000, dest_addr="bcrt1pp4m4dkldnss3thlcqzuyaj8368u3t9jc8mrpt7glsta7yepwalfqzlfqq9", vbyte_sats=1)
#node.send_onchain(send_onchain_req)

# Get invoice
new_invoice = node.get_invoice(sats=10)

# Pay invoice
inv = "lnbcrt10u1pj35xgusp5ukxahk59n2ufwn2pjkxug47fp5y4zzeegg9mky87t70d32zrv7nspp5dmx5eahjfek8f6k76mtdgc5hv588yczqjw7mvj8qwqm2nl266uwsdp92phkcctjypykuan0d93k2grxdaezqcmpwfhkcxqyjw5qcqp2rzjqv476yjr3gz9rvedq4a5d7exjf8a39pkxfcnxcydh738a9y05uj97qqqhqqqqqsqqqqqqqlgqqqqqqgq9q9qyysgqmzuvrtu2vrk4sgcancyezjfk4lmc6yvrue30rtqmkjc09fgucl09aumappqe0dnf0n0v5ej8700pdvrsurc4v2rah7h2vc7596tvswspx8cgpv"
pay_req = PayInvoiceRequest(invoice=inv, fee_limit_sats=10)
paid_invoice = node.pay_invoice(pay_req)

# Get opened channels
open_chans = node.get_opened_channels().unwrap()

# Get pending open channels
node.get_pending_open_channels()

# Open channel
open_req = OpenChannelRequest(
      peer_pubkey="02589e471abc2bd62529c52a5bed94f4085f939f9d6bceca6858dba357c5c12e4a",
      peer_host="172.18.0.4:19846",
      capacity=1_000_000,
      base_fee=0,
      ppm_fee=100,
      cltv_delta=144,
      min_htlc_sats=1,
      vbyte_sats=1      
)
node.open_channel(open_req)

# Close channel
chan_point = "" #TODO test closing channel
close_req = CloseChannelRequest(channel_point=open_chans[0].channel_point, vbyte_sats=1, is_force=False)
node.close_channel(close_req)