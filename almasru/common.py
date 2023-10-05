from typing import Callable
import logging


def check_error(fn: Callable) -> Callable:
    """Prevents operation if the record is containing an error

    :param fn: Method that should not to be executed in case of error

    :return: Wrapper function of the decorator
    """

    def wrapper(*args, **kwargs):
        """Wrapper function
        """
        rec = args[0]

        if rec.error is False and (rec.data is not None or (hasattr(rec, 'src_data') and rec.src_data is not None)):
            rec = fn(*args, **kwargs)
        else:
            logging.error(f'{repr(rec)}: due to error to the record, process "{fn.__name__}" skipped.')
        return rec

    wrapper.__doc__ = fn.__doc__

    return wrapper