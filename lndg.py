import requests
import json


class RecordList:
    """Useful class for filtering a list of dicts"""

    def __init__(self, list_of_dicts=False):
        self.list = list_of_dicts if list_of_dicts else []

    def sort(self, sort_func):
        return RecordList(list(sorted(sort_func, self.list)))

    def filter(self, filter_func):
        return RecordList(list(filter(filter_func, self.list))) if self.list else self

    def sum(self, key):
        return sum(r[key] for r in self.list if key in r)


class Lndg:
    def __init__(self, config, mempool, log):
        self.log = log
        self.mempool = mempool
        self.auth_user = config['auth_user']
        self.auth_pass = config['auth_pass']
        self.api_url = config['api_url']
        self.invoices = RecordList()
        self.payments = RecordList()
        self.onchain = RecordList()
        self.closures = RecordList()
        self.forwards = RecordList()

    def lndg_request(self, url, acc):
        req = requests.get(url, auth=(self.auth_user, self.auth_pass))
        res = json.loads(req.content)
        acc.list.extend(res['results'])
        if res['next']:
            self.lndg_request(res['next'], acc)

    def get_url(self, endpoint):
        return f"{self.api_url}{endpoint}/?format=json"

    def get_invoices(self):
        self.lndg_request(self.get_url('invoices'), self.invoices)
        return self.invoices

    def get_payments(self):
        self.lndg_request(self.get_url('payments'), self.payments)
        return self.payments

    def get_onchain(self):
        self.lndg_request(self.get_url('onchain'), self.onchain)
        return self.onchain

    def get_closures(self):
        self.lndg_request(self.get_url('closures'), self.closures)
        return self.closures

    def get_forwards(self):
        self.lndg_request(self.get_url('forwards'), self.forwards)
        return self.forwards
