from pathlib import Path
from collections import namedtuple
import pandas as pd
import math
import functools
from collections import defaultdict
from itertools import product
import numpy as np
from scipy.spatial.distance import cdist
import logging
import copy
from city_slickers.request import Request, parse_request
from city_slickers.utils import get_input
from city_slickers.utils import initialize_vehicle
from city_slickers.utils import initialize_bike_locations
from city_slickers.utils import random_coordinates
import networkx as nx

import logging.config
import logging
from joblib import Parallel, delayed


logging.config.fileConfig(fname="src/city_slickers/logging.ini", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def main(file):
    # Read Data
    file = Path(file)
    city_instructions, requests = get_input(file)
    iterate_paths(requests, city_instructions.bikes)


def get_revenue(starting_position, request):
    rev_mask = [True if tuple(starting_position) == tuple(position) else False for position in request.get_possible_locations()]
    return request.revenue[rev_mask][0][0]


class Node:
    def __init__(self, request, parent=None):
        self.parent = parent
        self.request = request
        self.request_time = request.request_time
        self.value = 0
        self.children = []
        self.max_value = 0
        self.booked = False

    def __repr__(self):
        return f"Node(request_id={self.request.request_id}, request_time={self.request_time}, value={self.value}, max_value={self.max_value}, parent={self.parent})"


def _max_rev_start(request):
    pickup_spots = request.get_possible_locations()
    time_booked = request.time_booked
    revenue = request.revenue
    rev_time = np.hstack([revenue, time_booked, pickup_spots])

    max_revenue_mask = [True if rev[0] == max(rev_time[:, 0]) else False for rev in rev_time]
    return tuple(rev_time[max_revenue_mask][0, 2:]), request.revenue[max_revenue_mask][0][0]


def _min_time_start(request):
    pickup_spots = request.get_possible_locations()
    time_booked = request.time_booked
    revenue = request.revenue
    time_pu = np.hstack([time_booked, pickup_spots])
    min_time_booked = [True if time == min(time_pu[:,0]) else False for time in time_pu[:,0]]
    return tuple(time_pu[min_time_booked][0,1:]), request.revenue[min_time_booked][0][0]


def get_traversals(T, g, node, requests, start=False, init_method='max_revenue'):

    if start:
        if init_method == 'shortest_time':
            position, revenue = _min_time_start(node.request)
        elif init_method == 'max_revenue':
            position, revenue = _max_rev_start(node.request)

    # Get Children
    children = list(T[node.request])

    # get revenue to this node from parent
    if node.parent is not None:
        revenue = get_revenue(node.parent.request.ending_position, node.request)  

    # If no children, get final value from this path
    if len(children) == 0:
        node.value = revenue
        node.max_value = revenue
        return node
    else:
        # For each children, get revenue to chil
        for child in children:
            child_node = Node(request=child, parent=node)
            edge_data = g.get_edge_data(requests[node.request.request_id], requests[child_node.request.request_id])
            node.children.append(get_traversals(T, g, child_node, requests))

        # Value this node as max revenue from children
        node.value = revenue
        node.max_value = revenue + max(node.children, key=lambda x :x.max_value).max_value
        return node


# Build Temporal Grid
def build_temporal_grid(requests):
    temporal_grid = defaultdict(lambda: defaultdict(list))
    for req in requests:
        for pickup_site in req.get_possible_locations():
            temporal_grid[req.request_time][tuple(pickup_site)].append(req)
    return temporal_grid


# create DAG
def create_dag(requests):
    g = nx.DiGraph()
    for request in requests:
        g.add_node(request, request_time=request.request_time)
    return g


# ADD EDGES
def add_dag_edges(g, requests, temporal_grid, seconds_from_max=None):
    if seconds_from_max is None:
        max_request_time = max(requests, key=lambda x: x.request_time).request_time
        seconds_from_current = max_request_time
    
    Parallel(n_jobs=3)(delayed(add_dag_edge)(g, request, seconds_from_current,temporal_grid) for request in requests)
    # for request in requests:
    #     mask = [True if tuple(request.starting_position) == tuple(position) else False for position in request.get_possible_locations()]
    #     arrival_time = request.arrival_time[mask][0][0]
    #     revenue = request.revenue[mask][0][0]

    #     position = tuple(request.ending_position)
    #     for second in range(seconds_from_current):
    #         results = temporal_grid[arrival_time+second][position]
    #         if results == []:
    #             continue
    #         else:
    #             for result in results:
    #                 if result.request_time < arrival_time:
    #                     continue
    #                 time_to_booking = result.request_time - request.time_booked[mask][0][0]
    #                 g.add_edge(request, result, time_to_booking=time_to_booking, revenue=revenue)
    return g


def add_dag_edge(g, request, seconds_from_current, temporal_grid):
    mask = [True if tuple(request.starting_position) == tuple(position) else False for position in request.get_possible_locations()]
    arrival_time = request.arrival_time[mask][0][0]
    revenue = request.revenue[mask][0][0]

    position = tuple(request.ending_position)
    for second in range(seconds_from_current):
        results = temporal_grid[arrival_time+second][position]
        if results == []:
            continue
        else:
            for result in results:
                if result.request_time < arrival_time:
                    continue
                time_to_booking = result.request_time - request.time_booked[mask][0][0]
                g.add_edge(request, result, time_to_booking=time_to_booking, revenue=revenue)
    return None


def iterate_paths(requests, bikes):
    _cached_requests = copy.copy(requests)
    for i in range(bikes):
        results = build_paths(_cached_requests)
        print_path(results[0], i, _cached_requests)
        break


def build_paths(requests):
    # Read Data
    temporal_grid = build_temporal_grid(requests)
    g = create_dag(requests)
    g = add_dag_edges(g, requests, temporal_grid)

    result = []
    for request in requests:
        root = Node(request=request, parent=None)
        T = nx.bfs_tree(g, source=request)
        result.append(get_traversals(T, g, root, requests, start=True, init_method='max_revenue'))
    return sorted(result, key=lambda x: -x.max_value)


# Print paths
def print_path(node, bike, _cached_requests):
    try:
        _cached_requests.remove(node.request)
    except:
        return

    logger.info(f"{node.request_time}|RENT B{bike} R{node.request.request_id}")

    if len(node.children) == 0:
        return None
    else:
        print_path(max(node.children, key=lambda x: x.max_value), bike)
    return None




if __name__ == "__main__":
    file = r'data\raw\ctsten0244_input_3.txt'
    main(file)