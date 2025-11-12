from prometheus_client import Counter, Gauge

class Metrics:
    def __init__(self):
        self.transactions_processed = Counter('transactions_processed', 'Number of transactions processed')
        self.active_connections = Gauge('active_connections', 'Number of active connections')