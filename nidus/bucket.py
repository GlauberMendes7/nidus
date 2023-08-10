import time


class Bucket:
    """
    Leaking bucket from: https://github.com/mpetyx/lotus_eaters/blob/master/lotus_eaters/bucket.py
    """

    def __init__(self, capacity: float, rate: float, value: float = None):
        self.__last_leak_time: float = None

        self.capacity: float = capacity
        self.rate: float = rate

        if value is not None:
            if value < 0:
                raise ValueError(
                    f"Current should should not be less than 0 (current={value}).")

            if value > capacity:
                raise ValueError(
                    f"Initial value should not be more than capacity (current={value}, capacity={capacity}).")
        else:
            value = capacity

        self.value: float = value

    def __leak(self):
        current_time = time.time()

        elapsed = current_time - self.__last_leak_time if self.__last_leak_time is not None else 0

        decrement = elapsed * self.rate

        if self.value - decrement >= 0:
            self.value = self.value - decrement

        self.__last_leak_time = current_time

        return self.value

    def consume(self, value=None):
        if value is None:
            value = 1

        current_value = self.__leak()

        expected_value = current_value + value

        if expected_value < 0 or expected_value > self.capacity:
            self.value = self.capacity
            return False

        self.value = expected_value

        return True
