from collections import namedtuple
from city_slickers.request import parse_request
import numpy as np
import logging
from random import choices

logger = logging.getLogger(__name__)
Instructions = namedtuple('Instructions', field_names=['requests', 'bikes', 'trucks', 'max_bikes_per_truck', 'base_rate'])


class Incrementer:
    def __init__(self):
        self.increment = -1

    def __call__(self):
        self.increment += 1
        return self.increment


def get_input(file):
    with open(file, 'r', encoding='utf-8') as f:
        docs = f.read().splitlines()
        docs = [row.split(' ') for row in docs]

    city_instructions = Instructions(*list(map(int, docs[0])))

    request_id_incrementer = Incrementer()
    return city_instructions, [parse_request(doc, city_instructions, request_id_incrementer) for doc in docs[1:]]


def random_coordinates(grid):
    return (np.random.randint(grid.min(),grid.max()), np.random.randint(grid.min(),grid.max()))


def print_coordinates(coord):
    logger.info(' '.join([str(int(pos)) for pos in coord]))


def initialize_vehicle(vehicle_count, vehicle_class, positions, requests=None, max_bikes=None):
    id_num = Incrementer()
    vehicles = []
    for position in positions:
        if max_bikes is None:
            _vehicle = vehicle_class(id_num=id_num(), position=position[:2], requests=requests)
            _vehicle.current_time = position[2]
            vehicles.append(_vehicle)
        else:
            _vehicle = vehicle_class(id_num=id_num(), position=position[:2], max_bikes=max_bikes)
            vehicles.append(_vehicle)
        logger.info(' '.join([str(int(pos)) for pos in position]))
    return vehicles


def initialize_bike_locations(requests, bikes, method='shortest', random_from_n_requests=None):
    if method == 'closest':
        return _init_bikes_closest(requests, bikes, random_from_n_requests)
    elif method == 'shortest':
        return _init_bikes_shortest_time(requests, bikes, random_from_n_requests)
    else:
        raise ValueError('mehotd must be one of closest')

def _init_bikes_shortest_time(requests, bikes, random_from_n_reqeusts) -> tuple:
    requests = sorted(requests, key=lambda x: (x.request_time, min(x.time_booked)))

    if random_from_n_reqeusts is not None:
        requests = choices(requests[:random_from_n_reqeusts], k=bikes)

    startingLocations = []
    for request in requests[:bikes]:
        startingLocations.append(tuple(np.hstack([request.starting_position, request.request_time])))
    return startingLocations


def _init_bikes_closest(requests, bikes, random_from_n_requests) -> tuple:
    requests = sorted(requests, key=lambda x: (x.request_time, -max(x.revenue)))
    startingLocations = []
    for request in requests[:bikes]:
        arr = np.hstack([request.get_possible_locations(), request.revenue, request.distance_walked])
        
        # Keep min revenue locations from trip
        # this allows us to get the bike back into ciruclation faster
        arr = arr[arr[:, 2] == arr[:, 2].min()]
        
        # Get minimum distance walked
        arr = arr[arr[:, 3] == arr[:, 3].min()][0]
        startingLocations.append(tuple(np.hstack([arr[:2], request.request_time])))

    return startingLocations