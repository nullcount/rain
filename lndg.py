import requests

class Lndg:
    def __init__(self, config, log):
        self.log = log
        self.auth_user = config['auth_user']
        self.auth_pass = config['auth_pass']
        self.api_url = config['api_url']
        self.invoices = []
        self.payments = []
        self.onchain = []
        self.closures = []
        self.forwards = []

    def lndg_request(self, endpoint):
        req = requests.get(f"{self.api_url}{endpoint}/?format=json", auth=(self.auth_user, self.auth_pass))
        return req.content

    def get_invoices(self):
        return self.lndg_request('invoices')
    def get_payments(self):
        return self.lndg_request('payments')
    def get_onchain(self):
        return self.lndg_request('onchain')
    def get_closures(self):
        return self.lndg_request('closures')
    def get_forwards(self):
        return self.lndg_request('forwards')

    def get_location(self):
        return self.location
