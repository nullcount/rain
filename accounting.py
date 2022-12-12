import os
import pickle
from datetime import datetime, date, timedelta
from lndg import Lndg, RecordList
from mempool import Mempool


class Accounting:
    def __init__(self, CREDS, log):
        self.log = log
        self.mempool = Mempool(CREDS['MEMPOOL'], log)
        self.lndg = Lndg(CREDS['LNDG'], self.mempool, log)
        self.history = None
        self.history_file = '.history.pkl'

    def save_history(self):
        with open(self.history_file, "wb") as p:
            pickle.dump(self.history, p)

    @staticmethod
    def get_apy(profits, total_funds, days_of_period):
        if total_funds == 0:
            return 0
        return (profits/total_funds) * (365 / days_of_period) * 100

    @staticmethod
    def ts_to_ord(d):
        return int(datetime.strptime(d.split("T")[0], "%Y-%m-%d").toordinal())

    @staticmethod
    def ord_to_datestr(o):
        return date.fromordinal(o).strftime("%Y-%m-%d")

    def get_history(self):
        self.history = {}
        if os.path.exists(self.history_file):
            with open(self.history_file, 'rb') as pickle_file:
                self.history = pickle.load(pickle_file)
        return self.sync_history()

    def add_ts(self, r):
        # very expensive operation -- lndg needs to add blocktimestamp to closures
        block_hash = self.mempool.get_block_hash(r['close_height'])
        ts = self.mempool.get_block_timestamp(block_hash)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")

    def sync_history(self):
        onchain_txs = None
        start_sync_from = 0
        yesterday = (date.today() - timedelta(1)).toordinal()
        if not self.history:
            # start at the oldest onchain tx timestamp day
            onchain_txs = self.lndg.get_onchain()
            start_sync_from = self.ts_to_ord(onchain_txs.list[0]['time_stamp'])
        else:
            # identify the last day with records in our history
            for day in self.history:
                d = int(datetime.strptime(day, "%Y-%m-%d").toordinal())
                if d > start_sync_from:
                    start_sync_from = d
            # already caught up -- will not index today
            if yesterday == start_sync_from:
                return self.history
        # query for data
        onchain_txs = self.lndg.get_onchain() if not onchain_txs else onchain_txs
        onchain_tx_hashes = [r['tx_hash'] for r in onchain_txs.list]
        channels_from_onchain_tx = RecordList(self.mempool.get_channels_from_txids(onchain_tx_hashes))
        closures = self.lndg.get_closures().add_key("time_stamp", self.add_ts)
        payments = self.lndg.get_payments().filter(lambda r: r['status'] == 2)
        invoices = self.lndg.get_invoices().filter(lambda r: r['state'] == 1 and r['is_revenue'])
        forwards = self.lndg.get_forwards()
        day = start_sync_from
        while yesterday > day:
            opens_to_date = channels_from_onchain_tx.filter(lambda r: day >= self.ts_to_ord(r['created']))
            payments_to_date = payments.filter(lambda r: day >= self.ts_to_ord(r['creation_date']))
            invoices_to_date = invoices.filter(lambda r: day >= self.ts_to_ord(r['settle_date']))
            onchain_txs_to_date = onchain_txs.filter(lambda r: day >= self.ts_to_ord(r['time_stamp']))
            forwards_to_date = forwards.filter(lambda r: day >= self.ts_to_ord(r['forward_date']))
            closures_to_date = closures.filter(lambda r: day >= self.ts_to_ord(r['time_stamp']))
            day_payments = payments_to_date.filter(lambda r: day == self.ts_to_ord(r['creation_date']))
            day_invoices = invoices_to_date.filter(lambda r: day == self.ts_to_ord(r['settle_date']))
            day_onchain_txs = onchain_txs_to_date.filter(lambda r: day == self.ts_to_ord(r['time_stamp']))
            day_forwards = forwards_to_date.filter(lambda r: day == self.ts_to_ord(r['forward_date']))
            day_closures = closures_to_date.filter(lambda r: day == self.ts_to_ord(r['time_stamp']))
            total_received = 0 if len(day_invoices.list) == 0 else int(day_invoices.sum('amt_paid'))
            revenue = 0 if len(day_forwards.list) == 0 else day_forwards.sum('fee')
            total_revenue = revenue + total_received
            close_fees = day_closures.sum('closing_costs') if len(day_closures.list) else 0
            onchain_costs = 0 if len(day_onchain_txs.list) == 0 else day_onchain_txs.sum('fee')
            onchain_costs += close_fees
            total_fees = 0 if len(day_payments.list) == 0 else int(day_payments.sum('fee'))
            profits = int(total_revenue-total_fees-onchain_costs)
            # find out how many sats are in local balance
            day_local_balance_in_channels = 0
            for chan in opens_to_date.list:
                day_local_balance_in_channels += chan['capacity']
            for chan in closures_to_date.list:
                day_local_balance_in_channels -= chan['settled_balance']
            for payment in payments_to_date.list:
                day_local_balance_in_channels -= (payment['value'] + payment['fee'])
            for invoice in invoices_to_date.list:
                day_local_balance_in_channels += invoice['amt_paid']
            for forward in forwards_to_date.list:
                day_local_balance_in_channels += forward['fee']
            day_date = self.ord_to_datestr(day)
            day_apy = self.get_apy(profits, day_local_balance_in_channels, 1)
            self.history[day_date] = {
                "onchain_costs": onchain_costs,
                "total_fees": total_fees,
                "total_revenue": total_revenue,
                "profits": profits,
                "apy": day_apy,
                "local_balance": day_local_balance_in_channels,

            }
            day += 1  # next day ordinal
        self.save_history()
        return self.history
