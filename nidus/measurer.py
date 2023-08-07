import psutil
import os
from pyJoules.energy_meter import EnergyContext, EnergyHandler


def foo(iterations=1000000):
    value = 0
    for iteration in range(iterations):
        value *= iteration

    return value


class Measure:
    def __init__(self):
        self.take_snapshot()

    def __take_snapshot_energy(self) -> dict:
        snapshot = dict()

        try:
            with EnergyContext(handler=EnergyHandler()) as energy:
                device_index = 0
                for device in energy.devices:
                    keys = device.get_configured_domains()
                    values = device.get_energy()

                    for i in range(len(keys)):
                        key_str = f"dev{device_index}_{str(keys[i])}"
                        snapshot[key_str] = values[i]
        except:
            pass
        
        return snapshot

    def __take_snapshot_ps(self) -> dict:
        snapshot = dict()

        p = psutil.Process(os.getpid())

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
    measure = Measure()

    for i in range(10):
        foo()
        print(measure.take_snapshot_delta())


if __name__ == "__main__":
    main()
