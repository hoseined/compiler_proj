def init_func(*args, exception_class):
    if args:
        exception_class.message = args[0]
    else:
        exception_class.message = None


def str_func(exception_type, exception_class):
    if exception_class.message:
        return "Scanner {} Error : {}".format(exception_type, exception_class.message)
    else:
        return "Scanner {} Error. No Error Message Supplied".format(exception_type)


class ScannerInitException(Exception):
    def __init__(self, *args):
        init_func(*args, exception_class=self)

    def __str__(self):
        return str_func('Init', self)


class ScannerTokenException(Exception):
    def __init__(self, *args):
        init_func(*args, exception_class=self)

    def __str__(self):
        return str_func('Token', self)
