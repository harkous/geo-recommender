import numpy as np

import sys

np.random.seed(1437)


def get_random_float(min,max):
    value = np.random.uniform(min,max)
    return np.float(value)


if __name__=='__main__':
    # print (get_random_float(-180,180))
    print (sys.getsizeof(150.1212))