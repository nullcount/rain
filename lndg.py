import requests
import json


class RecordList:
    """Useful class for filtering a list of dicts"""

    def __init__(self, list_of_dicts=False):
        self.list = list_of_dicts if list_of_dicts else []

    def filter(self, **kwargs):
        res = []
        for record in self.list:
            pass_filter = True
            for arg in kwargs:
                if "__" in arg:
                    a, operator = arg.split("__")
                    if operator == "gte" and isinstance(record[a], str) and not datetime.strptime(record[a], "%Y-%m-%dT%H:%M:%S") >= kwargs[arg]:
                        pass_filter = False
                        break
                    elif operator == "gte" and isinstance(record[a], int) and not record[a] >= kwargs[arg]:
                        pass_filter = False
                        break
                elif record[arg] != kwargs[arg]:
                    pass_filter = False
                    break
            if pass_filter:
                res.append(record)
        return RecordList(res)

    def sum(self, key):
        sum = 0
        for record in self.list:
            sum += record[key]
        return sum


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
