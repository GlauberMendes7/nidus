import psutil
from os import getpid
from pyJoules.energy_meter import EnergyContext, EnergyMeter, EnergyHandler


def foo(iterations=1000000):
    value = 0
    for iteration in range(iterations):
        value *= iteration

    return value


class Measure:
    def __init__(self, energy_context: EnergyContext = EnergyContext(handler=EnergyHandler())):
        self.energy_context: EnergyContext = energy_context
        self.energy_meter: EnergyMeter = None

    def __enter__(self):
        self.energy_meter = self.energy_context.__enter__()
        self.take_snapshot()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.energy_context.__exit__(exc_type, exc_value, exc_tb)
        self.energy_meter = None

        return self

    def __take_snapshot_energy(self) -> dict:
        if self.energy_meter is None:
            return {}

        snapshot = dict()

        device_index = 0
        for device in self.energy_meter.devices:
            keys = device.get_configured_domains()
            values = device.get_energy()

            for i in range(len(keys)):
                key_str = f"dev{device_index}_{str(keys[i])}"
                snapshot[key_str] = values[i]

        return snapshot

    def __take_snapshot_ps(self) -> dict:
        snapshot = dict()

        p = psutil.Process(getpid())

        def prefix_dict(prefix, a_dict): return {
            f"{prefix}_{key}": a_dict[key] for key in a_dict}

        snapshot.update(prefix_dict("mem", p.memory_full_info()._asdict()))
        snapshot.update(prefix_dict("cpu", p.cpu_times()._asdict()))

        return snapshot

    def take_snapshot(self) -> dict:
        self.snapshot = dict()
        self.snapshot.update(self.__take_snapshot_energy())
        self.snapshot.update(self.__take_snapshot_ps())
        return self.snapshot

    def get_snapshot(self) -> dict:
        return self.snapshot

    def take_snapshot_delta(self) -> dict:
        snapshot_last = self.get_snapshot()
        snapshot = self.take_snapshot()
        return {key: snapshot[key] - snapshot_last[key] for key in snapshot_last}


def main():
    with Measure() as measure:
        foo()
        print(measure.take_snapshot_delta())


if __name__ == "__main__":
    main()
