import numpy as np
from profilehooks import timecall
from utilities.geo_utils import get_geo_offsets
import os
from utilities.multiprocessing_utils import runInParallel
import argparse


class RealisticDataGenerator:
    def __init__(self, total_samples):
        """Setup and creation of directories

        Args:
            total_samples: number of samples to generate
        """
        self.total_samples = total_samples
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.source_data_location = os.path.join(dir_path, 'source_data')
        self.generated_data_location = os.path.join(dir_path, 'generated_data')

        os.makedirs(self.generated_data_location, exist_ok=True)

    def normalize_weights(self, weights):
        """Normalize the given weights to sum up to 1

        Args:
            weights:

        Returns: normalized weights

        """
        return weights / weights.sum()

    def get_random_samples(self, array, weights=None):
        """Get a total of self.total_samples random samples from the given array, with weighting option

        Args:
            array: array to sample from
            weights: optional weight parameter with the list weights to use

        Returns:

        """
        if weights is not None:
            return array[np.random.choice(array.shape[0], self.total_samples, p=weights.ravel())]
        else:
            return array[np.random.choice(array.shape[0], self.total_samples)]

    def produce_coordinates_with_offset(self):
        """Utility function to generate offsets for coordinates

        Returns:

        """
        print('generating coordinates')
        coords_data = np.genfromtxt(os.path.join(self.source_data_location, 'filtered_map_data.txt'), delimiter=',')
        coords = coords_data[:, :2]
        weights = coords_data[:, 2:]
        coords_offset = np.array([get_geo_offsets(lat, lon) for (lat, lon) in coords])
        concat = np.concatenate((coords, coords_offset, weights), axis=1)
        np.savetxt(os.path.join(self.source_data_location, 'coordinates_with_offsets.txt'), concat, fmt='%1.6f',
                   delimiter=',')

    @timecall
    def generate_coordinates(self):
        """Generates realistic coordinates based on the data, writes them into a file

        Returns:

        """
        print('generating coordinates')
        coords_data = np.genfromtxt(os.path.join(self.source_data_location, 'coordinates_with_offsets.txt'),
                                    delimiter=',')
        coords = coords_data[:, :4]
        weights = coords_data[:, 4:]
        #
        del coords_data

        weights = self.normalize_weights(weights)

        coords = self.get_random_samples(coords, weights=weights.ravel())

        # compute an offset in order to disperse the points in each square km
        factor = np.random.np.random.uniform(-1, 1, (self.total_samples, 2))
        offsets = coords[:, 2:]
        coords = coords[:, :2]
        coords = np.add(coords, np.multiply(offsets, factor))

        np.savetxt(os.path.join(self.generated_data_location, 'coords_' + str(self.total_samples) + '.txt'), coords,
                   fmt='%1.6f', delimiter=',')

    @timecall
    def generate_names(self):
        """Generates the names based on the datasets by joining first and last names (total of self.total_samples samples)
           Then it writes them into a file

        Returns:

        """
        print('generating names')
        # generate names
        first_names = np.genfromtxt(os.path.join(self.source_data_location, 'first_names_with_commas.txt'), dtype=str)
        last_names = np.genfromtxt(os.path.join(self.source_data_location, 'last_names.txt'), dtype=str)
        # todo: add a space after each name in the first names file to avoid the long process here
        first_names = self.get_random_samples(first_names)
        last_names = self.get_random_samples(last_names)
        names = np.core.defchararray.add(first_names, last_names)
        np.savetxt(os.path.join(self.generated_data_location, 'names_' + str(self.total_samples) + '.txt'), names,
                   fmt="%s")

    @timecall
    def generate_ages(self):
        """Generates the ages samples based on the datasets (weighing by distribution) and it writes them into a file

        Returns:

        """
        print('generating ages')
        ages_data = np.genfromtxt(os.path.join(self.source_data_location, 'world_age_distribution.txt'), dtype=int)
        ages = ages_data[:, :1].ravel()
        ages_weights = ages_data[:, 1:].ravel()
        ages_weights = self.normalize_weights(ages_weights)
        ages = self.get_random_samples(ages, weights=ages_weights)
        offset = np.random.choice(5, self.total_samples)
        ages = np.add(ages, offset)
        np.random.shuffle(ages)

        np.savetxt(os.path.join(self.generated_data_location, 'ages_' + str(self.total_samples) + '.txt'), ages,
                   fmt='%1.0f')

    @timecall
    def generate_data(self):
        """Generate the data in parallel into their files (using multiprocessing)

        Returns:

        """
        runInParallel(
            self.generate_names,
            self.generate_ages,
            self.generate_coordinates)
        # self.produce_coordinates_with_offset()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='realistic data generator')
    parser.add_argument('-s', '--size', help='number of data items', dest='size', required=True, type=int)
    args = parser.parse_args()

    r_gen = RealisticDataGenerator(args.size)
    r_gen.generate_data()
