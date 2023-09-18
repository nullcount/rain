import requests
from const import MEMPOOL_API_URL
from config import get_creds, log

class Mempool:
    def __init__(self):
        creds = get_creds('mempool')
        self.api_url = f"{creds.api_url}/api/v1" if creds.api_url else  MEMPOOL_API_URL

    def mempool_request(self, uri_path, data={}, obj=True):
        req = requests.get(
            self.api_url + uri_path,
            data=data
        )
        if obj:
            return req.json()
        else:
            return req.text

    def get_fee(self):
        return self.mempool_request("fees/recommended")

    def get_tip_height(self):
        return self.mempool_request("blocks/tip/height")

    def get_block_timestamp(self, block_hash):
        return self.mempool_request(f"block/{block_hash}")['timestamp']

    def get_block_hash(self, block_height):
        return self.mempool_request(f"block-height/{block_height}", obj=False)

    def get_mempool_bytes(self):
        res = self.mempool_request("mempool")
        return res['vsize'] if res['vsize'] else 0

    def get_channels_from_txids(self, txid_list):
        def chunks():
            for i in range(0, 20):
                yield txid_list[i::20]

        result = []
        for group_list in chunks():
            url_params = "?"
            for tx in group_list:
                url_params += f"txId[]={tx}&"
            res = self.mempool_request(f"lightning/channels/txids{url_params}", use_mempool=True)
            for r in res:
                if r['inputs']:
                    for i in r['inputs']:
                        result.append(r['inputs'][i])
                if r['outputs']:
                    for o in r['outputs']:
                        result.append(r['outputs'][o])
        return result

    def check_tx(self, tx_id):
        ret = self.mempool_request("tx/{0}".format(tx_id))
        return ret["status"]

