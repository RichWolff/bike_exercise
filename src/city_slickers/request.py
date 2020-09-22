import numpy as np
from itertools import product
from scipy.spatial.distance import cdist


class Request():
    def __init__(self, request_id, request_time, starting_position, ending_position, max_walk_distance, base_rate):
        self.request_id = request_id
        self.request_time = request_time
        self.starting_position = starting_position
        self.ending_position = ending_position
        self.max_walk_distance = max_walk_distance
        self.base_rate = base_rate

    @property
    def revenue(self):
        return self.distance_traveled + self.base_rate

    @property
    def available_bikes(self):
        res = []
        for bike in self.bikes:
            if bike.available == 1 and (self.distance_from_bike(bike) <= self.max_walk_distance):
                res.append(bike)

        return res

    def distance_from_bike(self, bike):
        return manhattan_distance(
            a=self.starting_position,
            b=bike.position
        )

    def get_possible_locations(self):
        if hasattr(self, 'possible_locations'):
            return self.possible_locations

        s = tuple(range(max(self.starting_position[0]-self.max_walk_distance, 0), self.starting_position[0]+self.max_walk_distance+1))
        e = tuple(range(max(self.starting_position[1]-self.max_walk_distance, 0), self.starting_position[1]+self.max_walk_distance+1))
        vals = np.array(list(product(s, e)))
        dists = cdist(np.array(self.starting_position).reshape(1, -1), vals, metric='cityblock')[0]
        self.possible_locations = np.unique(vals[dists <= self.max_walk_distance], axis=0)
        return self.possible_locations

    @property
    def time_to_travel(self):
        return np.ceil(self.distance_traveled / 2)

    @property
    def time_booked(self):
        return self.time_to_travel + self.distance_walked

    @property
    def distance_traveled(self):
        return cdist(self.get_possible_locations(), np.array(self.ending_position).reshape(1, -1), metric='cityblock')

    @property
    def distance_walked(self):
        return cdist(self.get_possible_locations(), np.array(self.starting_position).reshape(1, -1), metric='cityblock')

    @property
    def arrival_time(self):
        return self.request_time + self.distance_walked + np.ceil(self.distance_traveled / 2)

    @property
    def median_revenue(self):
        return np.median(self.revenue)

    def __sub__(self, other):
        return manhattan_distance(
            a=self.ending_position,
            b=other.starting_position
        )

    def __repr__(self, ):
        return f"""request(request_id={self.request_id}, request_time={self.request_time}, starting_position={self.starting_position}, ending_position={self.ending_position}, max_walk={self.max_walk_distance}, median_revenue={self.median_revenue})"""


def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def parse_request(doc, city_instructions, request_id):
    doc = list(map(int, doc))
    return Request(request_id(), doc[0], doc[1:3], doc[3:5], doc[5], city_instructions.base_rate)
