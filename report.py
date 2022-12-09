import time
import os
import pickle
from multiprocessing import Process
from lndg import Lndg
from mempool import Mempool
from config import CREDS
from datetime import datetime, timedelta
from prettytable import PrettyTable
import statistics
from scipy import stats
import numpy as np

DAY_BLOCKS = 144
MILLI = 1_000_000
HUNDO = 100
SAT_MSATS = 1_000

LNDG_CREDS = CREDS['LNDG']
MEMPOOL_CREDS = CREDS['MEMPOOL']

expensive_nodes = []


class Report:
    def __init__(self, node, log):
        self.node = node
        self.log = log
        self.mempool = Mempool(MEMPOOL_CREDS, log)
        self.lndg = Lndg(LNDG_CREDS, self.mempool, log)
        self.all_time_daily_apy = None
        if os.path.exists("daily_apy.pkl"):
            with open("daily_apy.pkl", "rb") as pickle_file:
                self.all_time_daily_apy = pickle.load(pickle_file)


    def make_report(self):
        report = ""
        report += self.table_profit_loss(self.get_profit_loss())
        return report

    def send_report(self):
        self.log.notify(self.make_report())
    
    def table_profit_loss(self, d):
        time = datetime.now().strftime("%m/%d/%Y")
        tables = []
        for t in ["1 Day", "7 Day", "30 Day", "90 Day", "Lifetime"]:
            key = "" if t == "Lifetime" else f"_{''.join(t.split(' ')).lower()}" 
            x = PrettyTable()
            x.add_column(time, ["Forwards", "Value", "Revenue", "Chain Costs", "LN Costs", "% Costs", "Profits"])
            x.add_column(t, [f"{d[f'forward_count{key}']:,}", f"{d[f'forward_amount{key}']:,}", f"{d[f'total_revenue{key}']:,} [{d[f'total_revenue_ppm{key}']:,}]", f"{d[f'onchain_costs{key}']:,}", f"{d[f'total_fees{key}']:,} [{d[f'total_fees_ppm{key}']:,}]", f"{d[f'percent_cost{key}']:,}%", f"{d[f'profits{key}']:,} [{d[f'profits_ppm{key}']:,}]"])
            tables.append(x)
        t = ""
        for table in tables:
            t += f"```\n{table}\n```"
        return t

        return tables

    def check_node_is_expensive(self, nodes):
        for node in nodes:
            fees = self.node.get_node_fee_report(node.pub_key)
            if fees['in_corrected_avg'] and fees['in_corrected_avg']> 1000 and fees['capacity'] > 100_000_000:
                expensive_nodes.put(fees)

    def get_node_fee_stats(self, nodeid):
        channels = self.node.get_node_channels(nodeid)
        in_ppm = []
        out_ppm = []
        capacity = 0
        capacities = []
        for c in channels:
            capacity += c.capacity
            capacities.append(c.capacity)
            if c.node1_pub == nodeid:
                out_ppm.append(c.node1_policy.fee_rate_milli_msat)
                in_ppm.append(c.node2_policy.fee_rate_milli_msat)
            else:
                out_ppm.append(c.node2_policy.fee_rate_milli_msat)
                in_ppm.append(c.node1_policy.fee_rate_milli_msat)

        # remove outliers and their corresponding capacities
        corrected_in_ppm, in_cap = self.remove_ppm_outliers(in_ppm, capacities)
        corrected_out_ppm, out_cap = self.remove_ppm_outliers(out_ppm ,capacities)

        # calculate weighted average
        corrected_weighted_in_ppm = np.average(corrected_in_ppm, weights=in_cap)
        corrected_weighted_out_ppm = np.average(corrected_out_ppm, weights=out_cap)

        return {"pub_key": nodeid, "channel_count": len(channels), "capacity": capacity, "in_min": min(in_ppm), "in_max": max(in_ppm), "in_avg": int(statistics.mean(in_ppm)), "in_corrected_avg": int(corrected_weighted_in_ppm), "in_med": int(statistics.median(in_ppm)), "in_std": int(statistics.stdev(in_ppm)) if len(in_ppm) >= 2 else None, "out_min": min(out_ppm), "out_max": max(out_ppm), "out_avg": int(statistics.mean(out_ppm)), "out_corrected_avg": int(corrected_weighted_out_ppm), "out_med": int(statistics.median(out_ppm)), "out_std": int(statistics.stdev(out_ppm)) if len(out_ppm) >= 2 else None}

    def remove_ppm_outliers(self, ppm_list, capacities):
        """
        remove outliers and their corresponding capacities (if applicable)
        in any case, return two numpy arrays
        """
        if len(ppm_list) < 2:
            return np.array(ppm_list), np.array(capacities)
        threshold = 3  # 99.7% of data points lie between +/- 3 std deviations
        absurd_fee = 1_000_000  # fee ppm above this would be too expenive to consider
        ppm_list = [ppm for ppm in ppm_list if ppm < absurd_fee]
        z = np.abs(stats.zscore(ppm_list))
        outlier_indices = np.where(z > threshold)
        if outlier_indices:
            corrected_ppm_list = np.delete(ppm_list, outlier_indices)
            corrected_capacities = np.delete(capacities, outlier_indices)
            return corrected_ppm_list, corrected_capacities
        else:
            return np.array(ppm_list), np.array(capacities)

    def get_expensive_nodes(self):
        tic = time.perf_counter()
        def chunks(l, n):
            """Yield n number of striped chunks from l."""
            for i in range(0, n):
                yield l[i::n]

        g = self.node.get_graph(refresh=True)
        thread_pool = []
        chunky = chunks(g.nodes, os.cpu_count() - 1)
        for chunk in chunky:
            t = Process(target=self.check_node_is_expensive, kwargs={"nodes":chunk})
            t.start()
            thread_pool.append(t)
        for thread in thread_pool:
            thread.join()
        toc = time.perf_counter()
        print(f"Finished in {toc - tic:0.4f} seconds")
        return expensive_nodes

    def get_profit_loss(self):
        block_height = self.mempool.get_tip_height()
        filter_90day = datetime.now() - timedelta(days=90)
        filter_30day = datetime.now() - timedelta(days=30)
        filter_7day = datetime.now() - timedelta(days=7)
        filter_1day = datetime.now() - timedelta(days=1)
        invoices = self.lndg.get_invoices().filter(state=1, is_revenue=True)
        invoices_90day = invoices.filter(settle_date__gte=filter_90day)
        invoices_30day = invoices.filter(settle_date__gte=filter_30day)
        invoices_7day = invoices.filter(settle_date__gte=filter_7day)
        invoices_1day = invoices.filter(settle_date__gte=filter_1day)
        payments = self.lndg.get_payments().filter(status=2)
        payments_90day = payments.filter(creation_date__gte=filter_90day)
        payments_30day = payments.filter(creation_date__gte=filter_30day)
        payments_7day = payments.filter(creation_date__gte=filter_7day)
        payments_1day = payments.filter(creation_date__gte=filter_1day)
        onchain_txs = self.lndg.get_onchain()
        onchain_txs_90day = onchain_txs.filter(time_stamp__gte=filter_90day)
        onchain_txs_30day = onchain_txs.filter(time_stamp__gte=filter_30day)
        onchain_txs_7day = onchain_txs.filter(time_stamp__gte=filter_7day)
        onchain_txs_1day = onchain_txs.filter(time_stamp__gte=filter_1day)
        closures = self.lndg.get_closures()
        closures_90day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 90))
        closures_30day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 30))
        closures_7day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS * 7))
        closures_1day = closures.filter(close_height__gte=(block_height - DAY_BLOCKS))
        forwards = self.lndg.get_forwards()
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
            'profits_ppm': 0 if forward_amount == 0 else int(profits/(forward_amount/MILLI)),
            'profits_ppm_90day': 0 if forward_amount_90day == 0 else int(profits_90day/(forward_amount_90day/MILLI)),
            'profits_ppm_30day': 0 if forward_amount_30day == 0 else int(profits_30day/(forward_amount_30day/MILLI)),
            'profits_ppm_7day': 0 if forward_amount_7day == 0 else int(profits_7day/(forward_amount_7day/MILLI)),
            'profits_ppm_1day': 0 if forward_amount_1day == 0 else int(profits_1day/(forward_amount_1day/MILLI)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*HUNDO),
            'percent_cost_90day': 0 if total_revenue_90day == 0 else int(((total_fees_90day+onchain_costs_90day)/total_revenue_90day)*HUNDO),
            'percent_cost_30day': 0 if total_revenue_30day == 0 else int(((total_fees_30day+onchain_costs_30day)/total_revenue_30day)*HUNDO),
            'percent_cost_7day': 0 if total_revenue_7day == 0 else int(((total_fees_7day+onchain_costs_7day)/total_revenue_7day)*HUNDO),
            'percent_cost_1day': 0 if total_revenue_1day == 0 else int(((total_fees_1day+onchain_costs_1day)/total_revenue_1day)*HUNDO),
        }
