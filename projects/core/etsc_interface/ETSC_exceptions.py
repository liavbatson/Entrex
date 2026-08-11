_DEFAULT_EXCEPTION_MESSAGE = "Missing data exception, consume could not find the requested data."


class ConsumeMissingDataException(Exception):
    def __init__(self, message=_DEFAULT_EXCEPTION_MESSAGE):
        super().__init__(message)
