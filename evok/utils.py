# Retry utility
# set logging for `retry` channel
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('retry')


# Define Exception class for retry
class RetryException(Exception):
    u_str = "Exception ({}) raised after {} tries."

    def __init__(self, exp, max_retry):
        self.exp = exp
        self.max_retry = max_retry
    def __unicode__(self):
        return self.u_str.format(self.exp, self.max_retry)
    def __str__(self):
        return self.__unicode__()


# Define retry util function
def retry_func(func, max_retry=10):
    """
    @param func: The function that needs to be retry
    @param max_retry: Maximum retry of `func` function, default is `10`
    @return: func
    @raise: RetryException if retries exceeded than max_retry
    """
    for retry in range(1, max_retry + 1):
        try:
            return func()
        except Exception as e:
            logger.info('Failed to call {}; e:{} in retry({}/{})'.format(func.func, e, retry, max_retry))
    else:
        raise RetryException(e, max_retry)