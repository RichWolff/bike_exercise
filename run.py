from city_slickers.utils import get_input
from city_slickers.utils import initialize_vehicle
from city_slickers.utils import initialize_bike_locations
from city_slickers.utils import random_coordinates
from city_slickers.vehicles import Truck, Bike
from pathlib import Path
import numpy as np
import logging.config
import logging
from collections import defaultdict


logging.config.fileConfig(fname="src/city_slickers/logging.ini", disable_existing_loggers=False)
logger = logging.getLogger(__name__)

FILE = Path(r"D:\Users\rwolff1\OneDrive - JNJ\sogeti_contest\data\raw\ctsten0244_input_2.txt")


def main():
    # Get instructions from input file
    city_instructions, requests = get_input(FILE)

    temporal_grid = defaultdict(lambda: defaultdict(list))
    for req in requests:
        for pickup_site in req.get_possible_locations():
            temporal_grid[req.request_time][tuple(pickup_site)].append(req)

    grid = np.array([[req.starting_position, req.ending_position] for req in requests], np.object).reshape(-1, 2)

    # Get bike starting points, Initialize Bikes and log separater
    # Returns x, y, time coordinates
    init_bike_locations = initialize_bike_locations(requests, city_instructions.bikes, method='shortest', random_from_n_requests=int(city_instructions.bikes*1.5))
    
    bikes = initialize_vehicle(city_instructions.bikes, Bike, requests=requests, positions=init_bike_locations)
    logger.info(" ")

    # Initialize Trucks and log separater
    init_truck_locations = [random_coordinates(grid) for _ in range(city_instructions.trucks)]
    trucks = initialize_vehicle(city_instructions.trucks, Truck, positions=init_truck_locations)
    logger.info(" ")

    bikes = sorted(bikes, key=lambda x: x.current_time)
    available_bikes = min(bikes, key=lambda x: x.current_time)

    for _ in range(30):
        bikes = find_requests(
            bikes=bikes,
            temporal_grid=temporal_grid,
            seconds_from_current=15,
            scoring_func='revenue',
            scoring_method='best'
        )

    logging.info(f'Total Revenue: {sum([b.revenue for b in bikes])}')


def find_requests(bikes, temporal_grid, seconds_from_current=1, scoring_func='time', scoring_method='best'):
    for bike in bikes:
        # Check if request is at the location of the bike
        # If yes, choose a fare
        fare = find_request(bike, temporal_grid, seconds_from_current, scoring_func, scoring_method)
        # if there are no fares, contineu
        if fare is None:
            continue
        logger.info(f"{int(bike.current_time)}|RENT B{bike.id} R{fare.request_id}")
        pickup_position_mask = [True if tuple(fare) == tuple(bike.position) else False for fare in fare.get_possible_locations()]
        bike.revenue += fare.revenue[pickup_position_mask][0][0]
        bike.position = fare.ending_position
        bike.current_time = fare.arrival_time[pickup_position_mask][0][0]
        # If no, is there a fare in the next n secons?
        # If No, find a truck and move to the next profitable spot
    return bikes


def find_request(bike, temporal_grid, seconds_from_current, scoring_func, scoring_method):
    requests = []
    for seconds in range(seconds_from_current):
        # Get requests at bike location and time plus seconds from current time
        requests.extend(temporal_grid[bike.current_time+seconds][tuple(bike.position)])

    # if there are no requests return empty list
    if len(requests) == 0:
        return None

    # If multiple, choose scoring function
    if scoring_func == 'time' and scoring_method == 'best':
        requests = sorted(requests, key=lambda x: min(x.time_booked))[0]
    elif scoring_func == 'revenue' and scoring_method == 'best':
        requests = sorted(requests, key=lambda x: -max(x.revenue))[0]

    return requests


if __name__ == '__main__':
    main()
