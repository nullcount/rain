import requests
import json
from datetime import datetime, timedelta

DAY_BLOCKS = 144
MILLI = 1_000_000
HUNDO = 100
SAT_MSATS = 1_000


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

    def get_profit_loss(self):
        block_height = self.mempool.get_tip_height()
        filter_90day = datetime.now() - timedelta(days=90)
        filter_30day = datetime.now() - timedelta(days=30)
        filter_7day = datetime.now() - timedelta(days=7)
        filter_1day = datetime.now() - timedelta(days=1)
        invoices = self.get_invoices().filter(state=1, is_revenue=True)
        invoices_90day = invoices.filter(settle_date__gte=filter_90day)
        invoices_30day = invoices.filter(settle_date__gte=filter_30day)
        invoices_7day = invoices.filter(settle_date__gte=filter_7day)
        invoices_1day = invoices.filter(settle_date__gte=filter_1day)
        payments = self.get_payments().filter(status=2)
        payments_90day = payments.filter(creation_date__gte=filter_90day)
        payments_30day = payments.filter(creation_date__gte=filter_30day)
        payments_7day = payments.filter(creation_date__gte=filter_7day)
        payments_1day = payments.filter(creation_date__gte=filter_1day)
        onchain_txs = self.get_onchain()
        onchain_txs_90day = onchain_txs.filter(time_stamp__gte=filter_90day)
        onchain_txs_30day = onchain_txs.filter(time_stamp__gte=filter_30day)
        onchain_txs_7day = onchain_txs.filter(time_stamp__gte=filter_7day)
        onchain_txs_1day = onchain_txs.filter(time_stamp__gte=filter_1day)
        closures = self.get_closures()
        closures_90day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 90))
        closures_30day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 30))
        closures_7day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 7))
        closures_1day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS))
        forwards = self.get_forwards()
        forwards_90day = forwards.filter(forward_date__gte=filter_90day)
        forwards_30day = forwards.filter(forward_date__gte=filter_30day)
        forwards_7day = forwards.filter(forward_date__gte=filter_7day)
        forwards_1day = forwards.filter(forward_date__gte=filter_1day)
        forward_count = len(forwards.list)
        forward_count_90day = len(forwards_90day.list)
        forward_count_30day = len(forwards_30day.list)
        forward_count_7day = len(forwards_7day.list)
        forward_count_1day = len(forwards_1day.list)
        forward_amount = 0 if forward_count == 0 else int(forwards.sum('amt_out_msat')/SAT_MSATS)
        forward_amount_90day = 0 if forward_count_90day == 0 else int(forwards_90day.sum('amt_out_msat')/SAT_MSATS)
        forward_amount_30day = 0 if forward_count_30day == 0 else int(forwards_30day.sum('amt_out_msat')/SAT_MSATS)
        forward_amount_7day = 0 if forward_count_7day == 0 else int(forwards_7day.sum('amt_out_msat')/SAT_MSATS)
        forward_amount_1day = 0 if forward_count_1day == 0 else int(forwards_1day.sum('amt_out_msat')/SAT_MSATS)
        total_revenue = 0 if forward_count == 0 else int(forwards.sum('fee'))
        total_revenue_90day = 0 if forward_count_90day == 0 else int(forwards_90day.sum('fee'))
        total_revenue_30day = 0 if forward_count_30day == 0 else int(forwards_30day.sum('fee'))
        total_revenue_7day = 0 if forward_count_7day == 0 else int(forwards_7day.sum('fee'))
        total_revenue_1day = 0 if forward_count_1day == 0 else int(forwards_1day.sum('fee'))
        total_received = 0 if len(invoices.list) == 0 else int(invoices.sum('amt_paid'))
        total_received_90day = 0 if len(invoices_90day.list) == 0 else int(invoices_90day.sum('amt_paid'))
        total_received_30day = 0 if len(invoices_30day.list) == 0 else int(invoices_30day.sum('amt_paid'))
        total_received_7day = 0 if len(invoices_7day.list) == 0 else int(invoices_7day.sum('amt_paid'))
        total_received_1day = 0 if len(invoices_1day.list) == 0 else int(invoices_1day.sum('amt_paid'))
        total_revenue += total_received
        total_revenue_90day += total_received_90day
        total_revenue_30day += total_received_30day
        total_revenue_7day += total_received_7day
        total_revenue_1day += total_received_1day
        total_revenue_ppm = 0 if forward_amount == 0 else int(total_revenue/(forward_amount/MILLI))
        total_revenue_ppm_90day = 0 if forward_amount_90day == 0 else int(total_revenue_90day/(forward_amount_90day/MILLI))
        total_revenue_ppm_30day = 0 if forward_amount_30day == 0 else int(total_revenue_30day/(forward_amount_30day/MILLI))
        total_revenue_ppm_7day = 0 if forward_amount_7day == 0 else int(total_revenue_7day/(forward_amount_7day/MILLI))
        total_revenue_ppm_1day = 0 if forward_amount_1day == 0 else int(total_revenue_1day/(forward_amount_1day/MILLI))
        total_sent = 0 if len(payments.list) == 0 else int(payments.sum('value'))
        total_sent_90day = 0 if len(payments_90day.list) == 0 else int(payments_90day.sum('value'))
        total_sent_30day = 0 if len(payments_30day.list) == 0 else int(payments_30day.sum('value'))
        total_sent_7day = 0 if len(payments_7day.list) == 0 else int(payments_7day.sum('value'))
        total_sent_1day = 0 if len(payments_1day.list) == 0 else int(payments_1day.sum('value'))
        total_fees = 0 if len(payments.list) == 0 else int(payments.sum('fee'))
        total_fees_90day = 0 if len(payments_90day.list) == 0 else int(payments_90day.sum('fee'))
        total_fees_30day = 0 if len(payments_30day.list) == 0 else int(payments_30day.sum('fee'))
        total_fees_7day = 0 if len(payments_7day.list) == 0 else int(payments_7day.sum('fee'))
        total_fees_1day = 0 if len(payments_1day.list) == 0 else int(payments_1day.sum('fee'))
        total_fees_ppm = 0 if total_sent == 0 else int(total_fees/(total_sent/MILLI))
        total_fees_ppm_90day = 0 if total_sent_90day == 0 else int(total_fees_90day/(total_sent_90day/MILLI))
        total_fees_ppm_30day = 0 if total_sent_30day == 0 else int(total_fees_30day/(total_sent_30day/MILLI))
        total_fees_ppm_7day = 0 if total_sent_7day == 0 else int(total_fees_7day/(total_sent_7day/MILLI))
        total_fees_ppm_1day = 0 if total_sent_1day == 0 else int(total_fees_1day/(total_sent_1day/MILLI))
        onchain_costs = 0 if len(onchain_txs.list) == 0 else onchain_txs.sum('fee')
        onchain_costs_90day = 0 if len(onchain_txs_90day.list) == 0 else onchain_txs_90day.sum('fee')
        onchain_costs_30day = 0 if len(onchain_txs_30day.list) == 0 else onchain_txs_30day.sum('fee')
        onchain_costs_7day = 0 if len(onchain_txs_7day.list) == 0 else onchain_txs_7day.sum('fee')
        onchain_costs_1day = 0 if len(onchain_txs_1day.list) == 0 else onchain_txs_1day.sum('fee')
        close_fees = closures.sum('closing_costs') if len(closures.list) else 0
        close_fees_90day = closures_90day.sum('closing_costs') if len(closures_90day.list) else 0
        close_fees_30day = closures_30day.sum('closing_costs') if len(closures_30day.list) else 0
        close_fees_7day = closures_7day.sum('closing_costs') if len(closures_7day.list) else 0
        close_fees_1day = closures_1day.sum('closing_costs') if len(closures_1day.list) else 0
        onchain_costs += close_fees
        onchain_costs_90day += close_fees_90day
        onchain_costs_30day += close_fees_30day
        onchain_costs_7day += close_fees_7day
        onchain_costs_1day += close_fees_1day
        profits = int(total_revenue-total_fees-onchain_costs)
        profits_90day = int(total_revenue_90day-total_fees_90day-onchain_costs_90day)
        profits_30day = int(total_revenue_30day-total_fees_30day-onchain_costs_30day)
        profits_7day = int(total_revenue_7day-total_fees_7day-onchain_costs_7day)
        profits_1day = int(total_revenue_1day-total_fees_1day-onchain_costs_1day)
        return {
            'forward_count': forward_count,
            'forward_count_90day': forward_count_90day,
            'forward_count_30day': forward_count_30day,
            'forward_count_7day': forward_count_7day,
            'forward_count_1day': forward_count_1day,
            'forward_amount': forward_amount,
            'forward_amount_90day': forward_amount_90day,
            'forward_amount_30day': forward_amount_30day,
            'forward_amount_7day': forward_amount_7day,
            'forward_amount_1day': forward_amount_1day,
            'total_revenue': total_revenue,
            'total_revenue_90day': total_revenue_90day,
            'total_revenue_30day': total_revenue_30day,
            'total_revenue_7day': total_revenue_7day,
            'total_revenue_1day': total_revenue_1day,
            'total_fees': total_fees,
            'total_fees_90day': total_fees_90day,
            'total_fees_30day': total_fees_30day,
            'total_fees_7day': total_fees_7day,
            'total_fees_1day': total_fees_1day,
            'total_fees_ppm': total_fees_ppm,
            'total_fees_ppm_90day': total_fees_ppm_90day,
            'total_fees_ppm_30day': total_fees_ppm_30day,
            'total_fees_ppm_7day': total_fees_ppm_7day,
            'total_fees_ppm_1day': total_fees_ppm_1day,
            'onchain_costs': onchain_costs,
            'onchain_costs_90day': onchain_costs_90day,
            'onchain_costs_30day': onchain_costs_30day,
            'onchain_costs_7day': onchain_costs_7day,
            'onchain_costs_1day': onchain_costs_1day,
            'total_revenue_ppm': total_revenue_ppm,
            'total_revenue_ppm_90day': total_revenue_ppm_90day,
            'total_revenue_ppm_30day': total_revenue_ppm_30day,
            'total_revenue_ppm_7day': total_revenue_ppm_7day,
            'total_revenue_ppm_1day': total_revenue_ppm_1day,
            'profits': profits,
            'profits_90day': profits_90day,
            'profits_30day': profits_30day,
            'profits_7day': profits_7day,
            'profits_1day': profits_1day,
            'profits_ppm': 0 if forward_amount == 0  else int(profits/(forward_amount/MILLI)),
            'profits_ppm_90day': 0 if forward_amount_90day == 0  else int(profits_90day/(forward_amount_90day/MILLI)),
            'profits_ppm_30day': 0 if forward_amount_30day == 0  else int(profits_30day/(forward_amount_30day/MILLI)),
            'profits_ppm_7day': 0 if forward_amount_7day == 0  else int(profits_7day/(forward_amount_7day/MILLI)),
            'profits_ppm_1day': 0 if forward_amount_1day == 0  else int(profits_1day/(forward_amount_1day/MILLI)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*100),
            'percent_cost_90day': 0 if total_revenue_90day == 0 else int(((total_fees_90day+onchain_costs_90day)/total_revenue_90day)*HUNDO),
            'percent_cost_30day': 0 if total_revenue_30day == 0 else int(((total_fees_30day+onchain_costs_30day)/total_revenue_30day)*HUNDO),
            'percent_cost_7day': 0 if total_revenue_7day == 0 else int(((total_fees_7day+onchain_costs_7day)/total_revenue_7day)*HUNDO),
            'percent_cost_1day': 0 if total_revenue_1day == 0 else int(((total_fees_1day+onchain_costs_1day)/total_revenue_1day)*HUNDO),
        }
