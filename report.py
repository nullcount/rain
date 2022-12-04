import time
import schedule
from threading import Thread

class Report:
    def __init__(self, report_config, node, log):
        self.node = node
        self.log = log
        self.intervals = report_config['intervals'].split(" ")
        self.daily_time = report_config['daily_time']
        self.expensive_nodes = []

    def get_profit_loss(self):
        return

   
    def get_expensive_nodes(self):
        tic = time.perf_counter()
        def chunks(l, n):
            """Yield n number of striped chunks from l."""
            for i in range(0, n):
                yield l[i::n]

        def check_node_is_expensive(nodes):
            for node in nodes:
                fees = self.node.get_node_fee_report(node.pub_key)
                if fees and fees['out_corrected_avg']:
                    if fees['out_corrected_avg'] > 1000 and fees['capacity'] > 100_000_000:
                        print("$$$$")
                        self.expensive_nodes.append(fees)

        g = self.node.get_graph(refresh=True)
        thread_pool = []
        for chunk in chunks(g.nodes, 15):
            thread_pool.append(Thread(target=check_node_is_expensive, kwargs={"nodes":chunk}))
        for thread in thread_pool:
            thread.start()
        for thread in thread_pool:
            thread.join()
        toc = time.perf_counter()
        print(f"Downloaded the tutorial in {toc - tic:0.4f} seconds")
        return self.expensive_nodes

    def get_apy(self):
        return

    def make_report(self):
        self.get_expensive_nodes()
        return

    def mainLoop(self):
        self.make_report()
        #if "daily" in self.intervals:
        #    schedule.every().day.at(self.daily_time).do(self.make_report())

        #while True:
        #    schedule.run_pending()
        #    time.sleep(60)
