class Truck:
    def __init__(self, position, id_num):
        self.id = id_num
        self.position = position
        self.max_bikes = 0
        self.current_bikes = 0
        

    def __repr__(self):
        return f"Truck(id={self.id}, position={self.position}, max_bikes={self.max_bikes}, current_bikes={self.current_bikes})"


class Bike(Truck):
    def __init__(self, position, id_num, requests):
        super().__init__(position, id_num)
        self.revenue = 0
        self.current_time = 0
        self.request_list = requests
        self.close_requests = []

    def update_close_request():
        pass

    def __repr__(self):
        return f"Bike(id={self.id}, position={self.position}, revenue={self.revenue}, current_time={self.current_time})"
