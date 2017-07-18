import heapq
import json


class BoundedPriorityQueue:
    def __init__(self, bound):
        self._queue = []
        self._index = 0
        self.bound = bound

    def push(self, item, priority):
        """Push an item to the queue

        Args:
            item: item to be pushed
            priority: item priority

        Returns:

        """

        if self.size() >= self.bound:
            if priority >= -self.peek()[0]:
                return
            else:
                self.pop()

        heapq.heappush(self._queue, (-priority, self._index, item))
        self._index += 1

    def pop_item(self):
        """Obtain item object from the queue

        Returns: dictionary with the user item object

        """
        return heapq.heappop(self._queue)[-1]

    def pop(self):
        """Obtain raw queue item

        Returns: queue item, including distance, index, user dict

        """
        return heapq.heappop(self._queue)

    def peek(self):
        """Check the raw item that can be popped next

        Returns: raw queue item

        """
        if self.size() > 0:
            return self._queue[0]
        return None

    def peek_item(self):
        """Check the item that can be popped next

        Returns: user dict item

        """
        return self._queue[0][-1]

    def peek_item_priority(self):
        """Get priority of the item that can be popped next

        Returns: priority of the item that can be popped next

        """
        return -self._queue[0][0]

    def size(self):
        """Queue size

        Returns:

        """
        return len(self._queue)

    def __str__(self):
        printed_queue = [(-priority, item) for priority, index, item in self._queue]
        return printed_queue.__str__()

    def is_full(self):
        """

        Returns: True if the queue is full

        """
        return self.size() == self.bound

    def get_as_list(self,with_dist=False):
        """Returns the queue with the items as a sorted list in increasing distance order

        Returns: list of user items

        """
        list =[]
        while(self.size()>0):
            item = self.pop()
            data_item = item[2]
            newitem={
                'distance':-item[0],
                'longitude':data_item['longitude'],
                'latitude':data_item['latitude'],
                'name':data_item['name'],
                'age':data_item['age'],
            }
            if with_dist:
                newitem['distance']=-item[0]

            # (-item[0],item[1:])
            list.append(newitem )

        list.reverse()
        return list


if __name__ == '__main__':
    pq = BoundedPriorityQueue(2)

    pq.push('r', 10)
    print(pq)
    pq.push('a', 0.5)
    print(pq)
    pq.push('b', 1)
    print(pq)
    pq.push('c', 0)
    print(pq)
    print(pq.peek())
    print(pq.peek_item())
    print(pq.pop_item())
    print(pq)
