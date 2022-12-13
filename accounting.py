import os
import pickle
from datetime import datetime, date, timedelta
from lndg import Lndg, RecordList
from mempool import Mempool
from tqdm import tqdm


class Accounting:
    def __init__(self, CREDS, log):
        self.log = log
        self.mempool = Mempool(CREDS['MEMPOOL'], log)
        self.lndg = Lndg(CREDS['LNDG'], self.mempool, log)
        self.history = {}
        self.history_file = '.history.pkl'

    def save_history(self):
        with open(self.history_file, "wb") as p:
            pickle.dump(self.history, p)

    def load_history(self):
        if not os.path.exists(self.history_file):
            return  # nothing to load
        with open(self.history_file, 'rb') as pickle_file:
            self.history = pickle.load(pickle_file)

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
        if not self.history:
            self.load_history()
        return self.history

    def add_ts(self, r):
        # very expensive operation -- lndg needs to add blocktimestamp to closures
        block_hash = self.mempool.get_block_hash(r['close_height'])
        ts = self.mempool.get_block_timestamp(block_hash)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")

    def sync_history(self, progress=False):
        self.load_history()
        onchain_txs = None
        prog_bar = None
        start_sync_from = 0
        yesterday = (date.today() - timedelta(1)).toordinal()
        node_inception_date = float('inf')  # infinity
        if not self.history:
            # start at the oldest onchain tx timestamp day
            onchain_txs = self.lndg.get_onchain()
            start_sync_from = self.ts_to_ord(onchain_txs.list[0]['time_stamp'])
            node_inception_date = start_sync_from
        else:
            # identify the last day with records in our history
            for day in self.history:
                d = int(datetime.strptime(day, "%Y-%m-%d").toordinal())
                if d > start_sync_from:
                    start_sync_from = d
                if d < node_inception_date:
                    node_inception_date = d
            # already caught up -- will not index current day until tomorrow
            if yesterday == start_sync_from:
                return self.history
        # query for data
        if progress:
            print(f"Node alive for {yesterday - node_inception_date} days")
            print(f"Missing {yesterday - start_sync_from} days of historical data")
            print("Fetching latest records from LNDg...")
        onchain_txs = self.lndg.get_onchain() if not onchain_txs else onchain_txs
        onchain_tx_map = {}
        for tx in onchain_txs.list:
            onchain_tx_map[tx['tx_hash']] = tx
        onchain_tx_hashes = [r['tx_hash'] for r in onchain_txs.list]
        channels_from_onchain_tx = RecordList(self.mempool.get_channels_from_txids(onchain_tx_hashes))
        closures = self.lndg.get_closures().add_key("time_stamp", lambda r: onchain_tx_map[r['closing_tx']]['time_stamp'] if r['closing_tx'] in onchain_tx_map else self.add_ts(r))
        payments = self.lndg.get_payments().filter(lambda r: r['status'] == 2)
        invoices = self.lndg.get_invoices().filter(lambda r: r['state'] == 1 and r['is_revenue'])
        forwards = self.lndg.get_forwards()
        if progress:
            print(f"Starting sync from {self.ord_to_datestr(start_sync_from)}")
            prog_bar = tqdm(total=(yesterday - node_inception_date), initial=(start_sync_from - node_inception_date))
        days_to_sync = range(start_sync_from, yesterday + 1)
        for day in days_to_sync:
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
            day_apy = self.get_apy(profits, day_local_balance_in_channels, 1)
            day_date = self.ord_to_datestr(day)
            self.history[day_date] = {
                "onchain_costs": onchain_costs,
                "total_fees": total_fees,
                "total_revenue": total_revenue,
                "profits": profits,
                "apy": day_apy,
                "local_balance": int(day_local_balance_in_channels),

            }
            if progress: prog_bar.update(1)
        self.save_history()
        return self.history
