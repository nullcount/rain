import time
import schedule


class Report:
    def __init__(self, report_config, node, log):
        self.node = node
        self.log = log
        self.intervals = report_config['intervals'].split(" ")
        self.daily_time = report_config['daily_time']

    def get_profit_loss(self):
        return

    def get_expensive_nodes(self):
        return

    def get_apy(self):
        return

    def make_report(self):
        return

    def mainLoop(self):
        if "daily" in self.intervals:
            schedule.every().day.at(self.daily_time).do(self.make_report())

        while True:
            schedule.run_pending()
            time.sleep(60)
