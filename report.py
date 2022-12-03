import time


class Report:
    def __init__(self, report_config, node, log):
        self.node = node
        self.log = log
        self.interval = report_config['interval']

    def mainLoop(self):
        while True:
            time.sleep(512)
