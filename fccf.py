#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import sys


HWMON_PATH = Path("/sys/class/hwmon")


@dataclass()
class MonitorMapping():
    hwmon: str
    name: str

def get_needed_monitor_names() -> Optional[List[MonitorMapping]]:
    with open("/etc/fancontrol") as f:
        for line in f:
            if line.startswith("DEVNAME="):
                line = line.replace("DEVNAME=", "").strip()
                return [MonitorMapping(*mon.split("=")) for mon in line.split(" ")]
        return None


def update_fancontrol_conf(old: List[MonitorMapping], new: List[MonitorMapping]) -> None:
    with open("/etc/fancontrol") as f:
        config = f.read()

    for old_monitor in old:
        old_hwmon = old_monitor.hwmon
        new_hwmon = ""

        for new_monitor in new:
            if new_monitor.name == old_monitor.name:
                new_hwmon = new_monitor.hwmon
                break

        if old_hwmon != new_hwmon:
            print(f"Warning: updating {old_hwmon} to {new_hwmon}")
            config = config.replace(old_hwmon, new_hwmon)

    with open("/etc/fancontrol", "w") as f:
        f.write(config)


def fix_monitor_mappings(required: List[MonitorMapping], available: List[MonitorMapping]) -> List[MonitorMapping]:
    avail_map = {}
    for mon in available:
        avail_map[mon.name] = mon.hwmon

    result = []
    for mon in required:
        new_hwmon = avail_map.get(mon.name)
        if new_hwmon is None:
            print(f"Error: {mon.name} does not exist", file=sys.stderr)
            sys.exit(1)
        result.append(MonitorMapping(new_hwmon, mon.name))
    return result


def get_available_monitors() -> List[MonitorMapping]:
    monitors = []
    for mon_path in HWMON_PATH.glob("hwmon*"):
        with open(mon_path / "name") as name:
            monitors.append(MonitorMapping(mon_path.name, name.read().strip()))
    return monitors


if __name__ == "__main__":
    if not HWMON_PATH.exists() or not HWMON_PATH.is_dir():
        print(f"Error: {HWMON_PATH} does not exist or is not a directory", file=sys.stderr)
        sys.exit(1)

    required_monitors = get_needed_monitor_names()
    available_monitors = get_available_monitors()

    if not required_monitors or not available_monitors:
        print("Error: no required monitors or none available", file=sys.stdout)
        sys.exit(1)

    correct_monitors = fix_monitor_mappings(required_monitors, available_monitors)
    update_fancontrol_conf(required_monitors, correct_monitors)
