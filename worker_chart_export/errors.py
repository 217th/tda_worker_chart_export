class WorkerChartExportError(Exception):
    pass


class ConfigError(WorkerChartExportError):
    pass


class NotImplementedYetError(WorkerChartExportError):
    pass

