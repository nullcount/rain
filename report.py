import time
import schedule
import os
from multiprocessing import Process
import requests
import json

class Report:
    def __init__(self, report_config, node, log):
        self.node = node
        self.log = log
        self.intervals = report_config['intervals'].split(" ")
        self.daily_time = report_config['daily_time']
        self.expensive_nodes = []

    def get_profit_loss(self):
        req = requests.get('http://localhost:8889/api/invoices/?format=json', auth=("lndg-admin", "163f0f6988f7ba4eb065130db5ab591a9f81f12e9f56468350be2215147a493e"))
        print(req.content)
    
    def check_node_is_expensive(self, nodes):
        for node in nodes:
            fees = self.node.get_node_fee_report(node.pub_key)
            if fees['in_corrected_avg'] and fees['in_corrected_avg']> 1000 and fees['capacity'] > 100_000_000:
               self.expensive_nodes.append(fees)
               print(self.expensive_nodes)


   
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
        return self.expensive_nodes

    def get_apy(self):
        return

    def make_report(self):
        expensive = self.get_expensive_nodes()
        print(expensive)
        for n in expensive:
            print(self.node.get_node_alias(n['pub_key']))
            print(n['in_corrected_avg'])
        #self.get_profit_loss()
        return

    def mainLoop(self):
        self.make_report()
        #if "daily" in self.intervals:
        #    schedule.every().day.at(self.daily_time).do(self.make_report())

        #while True:
        #    schedule.run_pending()
        #    time.sleep(60)
