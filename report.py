import time
import os
from multiprocessing import Process
from lndg import Lndg
from mempool import Mempool
from config import Config

CREDS = Config('creds.config').config
LNDG_CREDS = CREDS['LNDG']
MEMPOOL_CREDS = CREDS['MEMPOOL']


class Report:
    def __init__(self, report_config, node, log):
        self.node = node
        self.log = log
        self.mempool = Mempool(MEMPOOL_CREDS, log)
        self.lndg = Lndg(LNDG_CREDS, self.mempool, log)
        self.intervals = report_config['intervals'].split(" ")
        self.daily_time = report_config['daily_time']

    def get_profit_loss(self):
        self.lndg.refresh_all_data()
        invoices = self.lndg.invoices.filter(state=1, is_revenue=True)
        print(invoices)
        return

    def check_node_is_expensive(self, nodes):
        for node in nodes:
            fees = self.node.get_node_fee_report(node.pub_key)
            if fees['in_corrected_avg'] and fees['in_corrected_avg']> 1000 and fees['capacity'] > 100_000_000:
                expensive_nodes.put(fees)
               # print(fees)

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

    def get_apy(self):
        return

    def make_report(self):
        #expensive = self.get_expensive_nodes()
        #while not expensive_nodes.empty():
        #    print(expensive_nodes.get())

        self.get_profit_loss()
        return

    def mainLoop(self):
        self.make_report()
        #if "daily" in self.intervals:
        #    schedule.every().day.at(self.daily_time).do(self.make_report())

        #while True:
        #    schedule.run_pending()
        #    time.sleep(60)
