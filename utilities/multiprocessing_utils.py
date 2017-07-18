import multiprocessing
from joblib import Parallel, delayed
from multiprocessing import Process
import sys

num_cores = multiprocessing.cpu_count()


def runInParallel(*fns):
    """Run the functions given in parallel over the num_cores given

    Args:
        *fns:

    Returns:

    """
    Parallel(n_jobs=max(1, num_cores * 5 // 6))(delayed(fn)() for fn in fns)
