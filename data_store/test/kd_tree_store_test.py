import unittest
from data_store.kd_tree_store import KDTreeDataStore
from data_generation.person import Person


class KDTreeDataStoreTest(unittest.TestCase):
    def test_get_median(self):
        item_list = [
            {'name':'hamza harkous','age': 18,'latitude':40.3,'longitude':13.3}, {'name':'John Doe','age': 40,'latitude':120.3,'longitude':-3.3},
            {'name': 'Doroles Doe', 'age': 80, 'latitude': 89.3, 'longitude':-59.3},
            {'name': 'Debby Smith', 'age': 35, 'latitude': 120.3, 'longitude':53.3},
            {'name': 'agent smith', 'age': 33, 'latitude': 90.3, 'longitude': 43.3},
            {'name': 'Jane Smith', 'age': 35, 'latitude': 110.3, 'longitude': 53.3},
            {'name': 'FLoat Number', 'age': 77, 'latitude': 60.3, 'longitude': -13.3}]

        left_item_set, right_item_set, median_item= KDTreeDataStore.get_median(item_list, 0)
        self.assertEqual(median_item, {'name': 'agent smith', 'age': 33, 'latitude': 90.3, 'longitude': 43.3})
        self.assertEqual(left_item_set, [{'longitude': 13.3, 'age': 18, 'name': 'hamza harkous', 'latitude': 40.3}, {'longitude': -13.3, 'age': 77, 'name': 'FLoat Number', 'latitude': 60.3}, {'longitude': -59.3, 'age': 80, 'name': 'Doroles Doe', 'latitude': 89.3}])
        self.assertEqual(right_item_set, [{'longitude': 53.3, 'age': 35, 'name': 'Jane Smith', 'latitude': 110.3}, {'longitude': -3.3, 'age': 40, 'name': 'John Doe', 'latitude': 120.3}, {'longitude': 53.3, 'age': 35, 'name': 'Debby Smith', 'latitude': 120.3}])
        # self.assertEqual(KDTreeDataStore.get_median(item_list, 1)[2],  {'name':'hamza harkous','age': 18,'latitude':40.3,'longitude':13.3})


if __name__ == "__main__":
    unittest.main()
