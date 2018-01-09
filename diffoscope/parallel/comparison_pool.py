import logging
import dill

from multiprocess import Pool
from diffoscope.config import Config
from functools import partial
from pickle import PickleError


logger = logging.getLogger(__name__)


class CommandFailedToExecute(Exception):
    def __init__(self, err):
        self.err = err
    def __str__(self):
        return repr(self.err)


class ComparisonPool(object):

  def __init__(self):
    self._pool = Pool()
    logger.debug("ComparisonPool initialized.")


  def map(self, fun, args=[], callback=None):
    logger.debug("Invoking parallel map for function %s", fun)

    pool = self._pool
    jobs = []

    def _callback(result, index):
      callback[index] = result


    for index, arg in enumerate(args):
      logger.debug("Adding new process for %s (%d: %s)", fun, index, arg)
      new_callback = partial(_callback, index=index)
      jobs.append(pool.apply_async(fun, args=(arg,), callback= new_callback))

    for job in jobs:
      try:
        job.get()
      except PickleError as e:
        raise CommandFailedToExecute(e)

      if not job.successful():
        raise CommandFailedToExecute(job._err_callback)

    logger.debug("Closing Pools")
    pool.close()
    pool.join()
    jobs = None
    logger.debug("Ending ComparisonPool.map")

