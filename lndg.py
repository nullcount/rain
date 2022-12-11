import requests
import json
from datetime import datetime


class RecordList:
    """Useful class for filtering a list of dicts"""

    def __init__(self, list_of_dicts=False):
        self.list = list_of_dicts if list_of_dicts else []

    def sort(self, key_name):
        return sorted(self.list, key=lambda d: int(d[key_name]))

    def filter(self, **kwargs):
        for arg in kwargs:
            if "__" in arg:
                a, op = arg.split("__")
                if op == "gte" and isinstance(self.list[0][a], str):
                    return RecordList(filter(self.list, key=lambda d: datetime.strftime(d[a], "%Y-%m-%dT%H:%M:%S") >= kwargs[arg]))
                elif op == "gte" and isinstance(self.list[0][a], int):
                    return RecordList(filter(self.list, key=lambda d: d[a] >= kwargs[arg]))
            else:
                return RecordList(filter(self.list, key=lambda d: d[a] != kwargs[arg]))

    def sum(self, key):
        return sum(self.list, key=lambda d: d[key])


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
