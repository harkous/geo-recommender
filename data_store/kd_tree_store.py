import numpy as np
import numpy.random as random
from data_store.bounded_priority_queue import BoundedPriorityQueue
from utilities.geo_utils import haversine_distance
import argparse
from profilehooks import timecall
from tqdm import tqdm
import bottle
from bottle import Bottle, request, response, run, abort
import time
import os.path
from utilities import file_utils
import redis
import multiprocessing
from multiprocessing import Process, Queue
import sys
from scipy import stats
import os.path

num_cores = multiprocessing.cpu_count()


class KDTreeDataStore():
    _median_sample = 10000
    _axis_keys = ['latitude', 'longitude']
    _num_axes = len(_axis_keys)

    use_approx_median = True

    def __init__(self, rebuild_index=False, redis_mode=True, data_from_file=True, data_list=None,
                 data_in_parallel=False,
                 size=100):
        """Initializes the store, reads the data, and construct the index

        Args:
            rebuild_index: rebuild index from scratch
            redis_mode: use redis backend
            data_from_file: when True, data is loaded from files; otherwise, data_list should give the list of data
            data_list: list of items to build the index from
            data_in_parallel: use multiprocessing to load data
            size:
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.generated_data_location = os.path.abspath(
            os.path.join(dir_path, os.pardir, './data_generation/generated_data/'))

        self.data_filename = '../data_generation/data_store_' + str(size) + '.p'

        if redis_mode:
            try:
                redis.Redis(host="localhost").ping()
            except:
                raise AssertionError('problem connecting to redis: make sure redis is up and running')

            try:
                self.r_server = redis.StrictRedis(host="localhost", charset="utf-8", decode_responses=True)
            except:
                raise AssertionError('problem connecting to redis: make sure redis is up and running')

        if (data_from_file and not redis_mode) or rebuild_index:

            self.ages_file = os.path.join(self.generated_data_location, 'ages_' + str(size) + '.txt')
            self.names_file = os.path.join(self.generated_data_location,
                                           'names_' + str(size) + '.txt')
            self.coords_file = os.path.join(self.generated_data_location,
                                            'coords_' + str(size) + '.txt')

            all_files_exist = file_utils.all_files_exist(self.ages_file, self.names_file, self.coords_file)
            if not all_files_exist:
                raise AssertionError(
                    "Data files are missing for this size. Generate them by running realistic_data_generator.py with --size argument of " + str(
                        size))

            self.load_data_from_file(data_in_parallel=data_in_parallel)
        else:
            self.data_list = data_list

        # key value store to store objects in by id. This is used to allow easy switching to redis
        self.kv_store = {}
        self.redis_mode = redis_mode
        # flag that is triggered in during index construction. This is used with redis to not heavily use redis when
        # constructing the index. Instead the values are stored in memory and batch-saved at the end.
        self._construction_phase = False

        if rebuild_index or not self.redis_mode:
            self.construct_index(item_list=self.data_list)

    def load_ages(self, filename):
        """Loads the ages data samples

        Args:
            filename: age samples' filename

        Returns: ages' numpy array

        """
        print('loading ages data')
        result = np.genfromtxt(filename, dtype=int)
        print('finished loading ages data')
        return result

    def load_names(self, filename):
        """Loads the names data samples

        Args:
            filename: names' samples filename

        Returns: names numpy array

        """
        print('loading names data')
        result = np.genfromtxt(filename, dtype=str)
        print('finished loading names data')
        return result

    def load_coords(self, filename):
        """Loads the coordinates' samples

        Args:
            filename: coordinates samples' filename

        Returns: coordinates numpy array

        """
        print('loading coords data')
        result = np.genfromtxt(filename, delimiter=',')
        print('finished loading coords data')
        return result

    # @timecall
    def load_data_from_file(self, data_in_parallel=False):
        """Loads the ages, names, and coordinates data into self.data_list

        Args:
            data_in_parallel: when True, data is loaded in parallel, using multiprocessing

        Returns: None

        """

        start_time = time.clock()

        if data_in_parallel:
            print('loading data from files with multiprocessing')

            nprocs = 3

            def worker(type, filename, out_q):
                """ The worker function, invoked in a process. 'nums' is a
                    list of numbers to factor. The results are placed in
                    a dictionary that's pushed to a queue.
                """
                result = {'type': type, 'data': None}
                if type == 'ages':
                    result['data'] = self.load_ages(filename)
                elif type == 'names':
                    result['data'] = self.load_names(filename)
                elif type == 'coords':
                    result['data'] = self.load_coords(filename)

                out_q.put(result)

            # Each process will get a queue to put its result into
            out_q = Queue()
            procs = []

            for item in [('ages', self.ages_file), ('names', self.names_file), ('coords', self.coords_file)]:
                p = multiprocessing.Process(
                    target=worker,
                    args=(item[0], item[1],
                          out_q))
                procs.append(p)
                p.start()

            # Collect all results into a single result dict. We know how many dicts
            # with results to expect.
            result = {}
            for i in range(nprocs):
                partial = out_q.get()
                result[partial['type']] = partial['data']

            # Wait for all worker processes to finish
            for p in procs:
                p.join()



        else:
            print('loading data in series')
            result = {'ages': None, 'names': None, 'coords': None}

            result['ages'] = self.load_ages(self.ages_file)
            result['names'] = self.load_names(self.names_file)
            result['coords'] = self.load_coords(self.coords_file)

        print('finished loading data from files to memory in: ', time.clock() - start_time, ' seconds')

        start_time = time.clock()
        print('now formatting the data')

        self.data_list = [
            {'id': str(i), 'age': int(k[0]), 'name': k[1], 'latitude': float(k[2][0]), 'longitude': float(k[2][1])} for
            i, k in enumerate(zip(result['ages'], result['names'], result['coords']))]

        print('finished formatting the loaded data in: ', time.clock() - start_time, ' seconds')

    time_success = 0
    time_total = 0

    @classmethod
    # @timecall
    def get_median(cls, item_set, axis):
        """Generates the median of the given item_set, either exactly or approximately (by
         computing the median of a set of constant size of _median_sample)

        Args:
            item_set: list of items whose median is to be computed
            axis: axis on which to compute the median (0 or 1)

        Returns: left_item_set, right_item_set, median

        """
        key = cls._axis_keys[axis]

        if cls.use_approx_median and len(item_set) >= cls._median_sample * 5:

            # take a random sample of the items of fixed size
            rand_indices = random.random_integers(0, len(item_set) - 1, size=cls._median_sample)
            sample_item_set = [item_set[ind] for ind in rand_indices]

            del rand_indices
            # get the points whose median is to be computed
            points = [item[key] for item in sample_item_set]

            args_sorted = np.argsort(points)
            median_index = len(points) // 2
            median = sample_item_set[args_sorted[median_index]]

            key_value = median[key]

            left_item_set = []
            right_item_set = []
            for item in item_set:
                if item['id'] != median['id']:
                    if item[key] <= key_value:
                        left_item_set.append(item)
                    else:
                        right_item_set.append(item)

            return left_item_set, right_item_set, median

        else:
            sample_item_set = item_set
            # get the points whose median is to be computed
            points = [item[key] for item in sample_item_set]

            args_sorted = np.argsort(points)
            median_index = len(points) // 2

            left_item_set = [sample_item_set[i] for i in args_sorted[:median_index]]
            right_item_set = [sample_item_set[i] for i in args_sorted[median_index + 1:]]
            median = sample_item_set[args_sorted[median_index]]

            return left_item_set, right_item_set, median

    # @timecall
    def profile_get_median(self, num_loops):
        """Utility function to profile the timing performance of median computation

        Args:
            num_loops: number of loops to test the median time performance

        Returns:

        """
        print('profiling the median computation')
        # self.load_data_from_file()
        time_list = []
        for i in tqdm(range(num_loops)):
            start_time = time.clock()
            self.get_median(self.data_list, i % 2)
            end_time = time.clock()
            time_list.append(end_time - start_time)
        average_time = np.average(time_list)
        print('\naverage time\n', average_time)
        return average_time

    def mem_set(self, key, value):
        """Set the item at key to value in self.kv_store or in redis

        Args:
            key:
            value:

        Returns:

        """
        if self.redis_mode and not self._construction_phase:
            self.r_server.set(key, value)
        else:
            self.kv_store[key] = value

    def hmem_set(self, key, value):
        """Set the dictionary at key to value in self.kv_store or in redis

        Args:
            key:
            value:

        Returns:

        """
        if self.redis_mode and not self._construction_phase:
            self.r_server.hmset(key, value)
        else:
            self.kv_store[key] = value

    def hgetall(self, key):
        """Get the dictionary at key from memory or redis

        Args:
            key:

        Returns:

        """
        if self.redis_mode and not self._construction_phase:
            return self.r_server.hgetall(key)
        else:
            return self.kv_store[key]

    def mem_get(self, key):
        """Get the value at key from memory or redis

        Args:
            key:

        Returns:

        """
        if self.redis_mode and not self._construction_phase:
            return self.r_server.get(key)
        else:
            return self.kv_store.get(key, None)

    def mem_incr(self, key):
        """Increment the value at key by 1 in memory or in redis

        Args:
            key:

        Returns:

        """
        if self.redis_mode and not self._construction_phase:
            self.r_server.incr(key)
        else:
            self.kv_store[key] = str(int(self.kv_store[key]) + 1)

    def mem_switch_to_redis(self):
        """Copies the context from memory to redis. This is triggered at the end of in-memory index construction

        Returns: None

        """
        p = self.r_server.pipeline()
        NUM_ENTRIES = len(self.kv_store)
        i = 0
        with tqdm(total=NUM_ENTRIES) as pbar:
            for key in list(self.kv_store):
                item = self.kv_store.pop(key)
                if type(item) is dict:
                    p.hmset(item['id'], item)
                elif type(item) is str:
                    p.set(key, item)

                pbar.update(1)
                i += 1

                if i % (100000) == 0:
                    p.execute()
                    p = self.r_server.pipeline()
            p.execute()

    # @timecall
    def construct_index(self, item_list=None):
        """Builds the index from an input item_list

        Args:
            item_list: list of items representing people

        Returns:

        """

        print('started building index from scratch')
        if self.redis_mode:
            self.r_server.flushdb()
        self._construction_phase = True

        with tqdm(total=len(item_list)) as pbar:
            root_id = self._construct_index(item_list, depth=0, pbar=pbar)

        self.mem_set('root_id', root_id)

        self._construction_phase = False

        if self.redis_mode:
            print('\nwriting cached items from construction phase to redis\n')
            self.mem_switch_to_redis()
            print('\nfinished updating index in redis\n')

    def _construct_index(self, item_list=None, depth=0, pbar=None):
        """Recursive helper function for index construction

        Args:
            item_list: list of items at current level
            depth: depth of the three
            pbar: progress bar object

        Returns:

        """
        # stopping condition when we reach the leaves
        if not item_list:
            return None

        axis = depth % self._num_axes
        start = time.clock()

        # get the median of the item list as a pivot element
        left_item_set, right_item_set, median_item = self.get_median(item_list, axis)

        pbar.update(1)

        # construct the left and right subtrees
        left_id = self._construct_index(left_item_set, depth + 1, pbar)
        right_id = self._construct_index(right_item_set, depth + 1, pbar)

        # add the id's of the left and right subtree roots to the current node
        self.add_node_properties(median_item, left_id=left_id, right_id=right_id)

        return median_item['id']

    @classmethod
    def get_coords(self, item):
        """get the (latitude,longitude) of an item

        Args:
            item:

        Returns: (latitude,longitude) tuple

        """
        return item['latitude'], item['longitude']

    def add_node_properties(self, item, left_id=None, right_id=None):
        """Adds to the node the ids of the left and right subtrees. Updates the memory location of the node

        Args:
            item: item dictionary
            left_id: id string of left subtree
            right_id: id string of right subtree

        Returns: None

        """
        item.update({'left_id': left_id, 'right_id': right_id})
        self.hmem_set(item['id'], item)

    def update_item_key(self, item, key, value):
        """Updates the value of the given key for the given item in redis

        Args:
            item:
            key:
            value:

        Returns:

        """
        self.r_server.hset(item['id'], key, value)

    # @timecall
    def distance(self, item, other_item, axis=None):
        """Computes the distance between two items (via their coordinates or along one axis)

        Args:
            item: first item
            other_item: item to compare with
            axis: (optional) allows choosing one axis to compute the distance on while keeping the other fixed. Used in KNN computation


        Returns:

        """
        if axis:
            key = self._axis_keys[axis]

            other_latitude = float(item['latitude']) if key == 'latitude' else float(other_item['latitude'])
            other_longitude = float(item['longitude']) if key == 'longitude' else float(other_item['longitude'])

            return haversine_distance(float(item['latitude']), float(item['longitude']), other_latitude,
                                      other_longitude)
        else:
            return haversine_distance(float(item['latitude']), float(item['longitude']), float(other_item['latitude']),
                                      float(other_item['longitude']))

    # @timecall
    def k_nearest_neighbors(self, target_item, k, age_proximity):
        """Compute the k nearest neighbors to the target_item given the age_proximity

        Args:
            target_item: user node
            k: number of neighbors
            age_proximity: maximum difference between a candidate neighbor's age and the user

        Returns: list of neighbors, sorted in ascending order of distance to the target_user

        """
        if not self.mem_get('root_id'):
            raise ValueError(
                'The index has not been created yet. Create before running the k_nearest_neighbors function')
        # create a bounded priority queue
        bp_queue = BoundedPriorityQueue(k)
        # call the recursive helper function
        self._k_nearest_neighbors(self.mem_get('root_id'), target_item, k, bp_queue, 0, age_proximity)
        # convert the queue to a list and sort it
        result = bp_queue.get_as_list(with_dist=True)
        result.sort(key=lambda l: l['distance'])
        return result

    def _k_nearest_neighbors(self, current_node_id, target_item, k, bp_queue, axis, age_proximity):
        """Recursive helper function for the k_nearest neighbor

        Args:
            current_node_id: current item in the recursion
            target_item: target user for which we want to recommend
            k:  number of neighbors
            bp_queue: bounded priority queue
            axis: axis on which to compute distances
            age_proximity: maximum difference between a candidate neighbor's age and the user

        Returns:

        """
        if not current_node_id:
            return

        current_node = self.get_node_from_id(current_node_id)

        axis %= self._num_axes
        key = self._axis_keys[axis]

        # calculate distance from current_item to target_item
        distance_to_target = self.distance(current_node, target_item)

        # compute the age difference with the target
        age_diff = abs(target_item['age'] - current_node['age'])

        # only add to the queue when the age difference is within range
        if age_diff <= age_proximity:
            bp_queue.push(current_node, distance_to_target)

        # go first to the subtree which gets us closer to the target location
        go_left = target_item[key] < current_node[key]
        # recursively search that subtree
        self._k_nearest_neighbors(current_node['left_id'] if go_left else current_node['right_id'],
                                  target_item, k, bp_queue, axis + 1, age_proximity)

        # if the candidate hypersphere intersects with the splitting plane, we
        # look at the other section of the plane by checking the other subtree
        if (not bp_queue.is_full()) \
                or self.distance(target_item, current_node, axis=axis) < bp_queue.peek_item_priority():
            self._k_nearest_neighbors(current_node['right_id'] if go_left else current_node['left_id'],
                                      target_item, k, bp_queue, axis + 1, age_proximity)

    def insert_item(self, target_item):
        """Inserts the target_item in the index

        Args:
            target_item:

        Returns:

        """

        # create new leaf node
        self.add_node_properties(target_item, left_id=None, right_id=None)
        # insert leaf in index
        return self._insert_item(self.mem_get('root_id'), target_item, 0)

    def get_node_from_id(self, id):
        """Gets the node from the memory or redis given its id

        Args:
            id: node id

        Returns: node object

        """
        result = self.hgetall(id)

        result['latitude'] = float(result['latitude'])
        result['longitude'] = float(result['longitude'])
        result['age'] = int(result['age'])

        if result['left_id'] == 'None':
            result['left_id'] = None
        if result['right_id'] == 'None':
            result['right_id'] = None
        return result

    def _insert_item(self, current_node_id, target_item, axis):
        """Helper recursive function for inserting an item into the index

        Args:
            current_node:
            target_item:
            axis:

        Returns:

        """

        if not current_node_id:
            self.mem_set('root_id', target_item['id'])

        current_node = self.get_node_from_id(current_node_id)
        axis %= self._num_axes
        key = self._axis_keys[axis]

        # go first to the subtree which gets us closer to the target location
        go_left = target_item[key] < current_node[key]

        if go_left and not current_node['left_id']:
            self.update_item_key(current_node, 'left_id', target_item['id'])
            return current_node_id

        elif not go_left and not current_node['right_id']:
            self.update_item_key(current_node, 'right_id', target_item['id'])
            return current_node_id

        else:
            return self._insert_item(current_node['left_id'] if go_left else current_node['right_id'],
                                     target_item, axis + 1)

    def find_item(self, target_item):
        """Allows looking up the node that matches the target_item coordinates

        Args:
            target_item:

        Returns:

        """
        return self._find_item(self.mem_get('root_id'), target_item, 0)

    def _find_item(self, current_node_id, target_item, axis):
        """Helper recursive function for finding a node

        Args:
            current_node_id:
            target_item:
            axis:

        Returns:

        """
        if not current_node_id:
            return None

        axis %= self._num_axes
        key = self._axis_keys[axis]

        current_node = self.get_node_from_id(current_node_id)

        if self.get_coords(current_node) == self.get_coords(target_item):
            return current_node

        else:
            # go first to the subtree which gets us closer to the target location
            go_left = target_item[key] < current_node[key]
            return self._find_item(current_node['left_id'] if go_left else current_node['right_id'],
                                   target_item, axis + 1)

    def print_index(self):
        """Prints the constructed index

        Returns: string of constructed index

        """
        return self._print_index(self.mem_get('root_id'), 0)

    def _print_index(self, current_node_id, level):
        """Helper recursive function for printing

        Args:
            current_node_id:
            level:

        Returns:

        """
        if not current_node_id:
            return None

        current_node = self.get_node_from_id(current_node_id)
        print('level ', level, current_node)

        self._print_index(current_node['left_id'], level + 1)
        self._print_index(current_node['right_id'], level + 1)

    def run_profiling(self, num_loops, num_neighbors, age_proximity):
        """Executes the k_nearest_neighbors algorithm for num_loops times and returns the average running time

        Args:
            num_loops: number of loops for which we query the server
            num_neighbors: number of neighbors to query for
            age_proximity: maximum difference between a candidate neighbor's age and the user


        Returns:

        """
        print('profiling over ', num_loops, ' times')
        random_latitudes = random.uniform(-90, 90, num_loops)
        random_longitudes = random.uniform(-180, 180, num_loops)
        time_list = []

        for i in tqdm(range(len(random_latitudes))):
            start_time = time.clock()
            kd_store.k_nearest_neighbors({'name': 'bla bla', 'age': 23, 'latitude': random_latitudes[i] / 2,
                                          'longitude': random_longitudes[i]}, num_neighbors, age_proximity)
            end_time = time.clock()
            time_list.append(end_time - start_time)

        # get the timing statistics
        stats_desc = stats.describe(time_list)
        frac_times_exceeded = len(np.where(np.array(time_list) >= 1)[0]) / len(time_list)
        print('\nfraction of times with delay > 1 is: ', frac_times_exceeded, '\n')
        print('\nStats:\n', stats_desc)
        return stats_desc

    def server_mode(self, port):
        """Launches the store in server mode on the given port

        Args:
            port: port to serve on

        Returns: None

        """

        app = Bottle()

        @app.hook('after_request')
        def enable_cors():
            """
            Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
            """
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
            response.headers[
                'Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        @app.route("/query", methods=['GET'])
        def query():
            """Query resp endpoint, requires latitude, longitude, and age

            Returns: sorted list of k nearest neighbors

            """
            try:
                latitude = request.query['latitude']
                longitude = request.query['longitude']
                age = request.query['age']

                latitude = float(latitude)
                longitude = float(longitude)
                age = int(age)

                result = self.k_nearest_neighbors(
                    {'name': 'bla bla', 'age': age, 'latitude': latitude, 'longitude': longitude}, 10, 5)

                return {'result': result}

            except:
                return bottle.HTTPResponse(status=404, body='Error: you need latitude, longitude, and age parameters')

        @app.route("/profile", methods=['GET'])
        def profile():
            """profiling rest -point

            Returns: profiling statistics

            """
            try:
                num_loops = int(request.query['num_loops'])
                num_neighbors = int(request.query['num_neighbors'])
                age_proximity = int(request.query['age_proximity'])

                stats_desc = self.run_profiling(num_loops, num_neighbors, age_proximity)
                return {'stats': stats_desc}
            except:
                print(sys.exc_info())
                return bottle.HTTPResponse(status=404,
                                           body="Error: you need the number of loops,the number of neighbors,"
                                                "and the age proximity value.")

        run(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='in memory data store using kd_trees')
    parser.add_argument('-s', '--size', help='number of data items', dest='size', required=True, type=int)
    parser.add_argument('-p', '--port', help='port to serve on', dest='port', default=5001, type=int)
    parser.add_argument('--redis_mode', action='store_true', help='activate redis mode', dest='redis_mode')
    parser.add_argument('--rebuild_index', action='store_true', help='rebuild index', dest='rebuild_index')

    args = parser.parse_args()

    print('generating index for data of size ', args.size)

    kd_store = KDTreeDataStore(rebuild_index=args.rebuild_index, redis_mode=args.redis_mode, size=args.size,
                               data_in_parallel=False)

    print('\ndone creating index\n')

    print('running initial time profiling for k-nearest neighbors: ')
    kd_store.run_profiling(100, 10, 5)

    kd_store.server_mode(args.port)
    #
    # if simple_test:
    #     data_list = [
    #         {'name': 'hamza harkous', 'age': 18, 'latitude': 40.3, 'longitude': 13.3},
    #         {'name': 'John Doe', 'age': 40, 'latitude': 120.3, 'longitude': -3.3},
    #         {'name': 'Doroles Doe', 'age': 80, 'latitude': 89.3, 'longitude': -59.3},
    #         {'name': 'Debby Smith', 'age': 35, 'latitude': 120.3, 'longitude': 53.3},
    #         {'name': 'agent smith', 'age': 33, 'latitude': 90.3, 'longitude': 43.3},
    #         {'name': 'Jane Smith', 'age': 35, 'latitude': 110.3, 'longitude': 53.3},
    #         {'name': 'FLoat Number', 'age': 77, 'latitude': 60.3, 'longitude': -13.3}]
    #
    #     kd_store = KDTreeDataStore(rebuild_index=True, redis_mode=False, data_from_file=False, data_list=data_list,
    #                                data_in_parallel=True)
    #
    #     kd_store.print_index()
    #     exit()
