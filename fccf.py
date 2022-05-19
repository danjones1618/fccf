#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import sys


HWMON_PATH = Path("/sys/class/hwmon")


@dataclass()
class MonitorMapping():
    path: Path
    hwmon: str
    name: str


def get_needed_monitor_names() -> Optional[List[MonitorMapping]]:
    paths = []
    names = []

    with open("/etc/fancontrol") as f:
        for line in f:
            if line.startswith("DEVNAME="):
                line = line.replace("DEVNAME=", "").strip()
                names = [mon.split("=") for mon in line.split(" ")]
            elif line.startswith("DEVPATH="):
                line = line.replace("DEVPATH=", "").strip()
                paths = [mon.split("=") for mon in line.split(" ")]

    needed = []
    for [path_hwname, path] in paths:
        for [names_hwname, name] in names:
            if path_hwname == names_hwname:
                needed.append(MonitorMapping(Path(path), path_hwname, name))
    return needed


def update_fancontrol_conf(old: List[MonitorMapping], new: List[MonitorMapping]) -> None:
    with open("/etc/fancontrol") as f:
        config = f.read()

    for old_monitor in old:
        new_mon: Optional[MonitorMapping] = None

        for new_monitor in new:
            if new_monitor.name == old_monitor.name:
                new_mon = new_monitor
                break

        if new_mon and old_monitor.hwmon != new_mon.hwmon:
            print(f"Warning: updating {old_monitor.hwmon} to {new_mon.hwmon}")
            config = config.replace(old_monitor.hwmon, new_mon.hwmon)

        if new_mon and old_monitor.path != new_mon.path:
            print(f"Warning: updating {old_monitor.path} to {new_mon.path}")
            config = config.replace(str(old_monitor.path), str(new_mon.path))

    with open("/etc/fancontrol", "w") as f:
        f.write(config)


def fix_monitor_mappings(required: List[MonitorMapping], available: List[MonitorMapping]) -> List[MonitorMapping]:
    avail_map: Dict[str, MonitorMapping] = {}
    for mon in available:
        avail_map[mon.name] = mon

    result = []
    for mon in required:
        new_hwmon = avail_map.get(mon.name)
        if new_hwmon is None:
            print(f"Error: {mon.name} does not exist", file=sys.stderr)
            sys.exit(1)
        result.append(MonitorMapping(new_hwmon.path, new_hwmon.hwmon, mon.name))
    return result


def get_available_monitors() -> List[MonitorMapping]:
    monitors = []
    for mon_path in HWMON_PATH.glob("hwmon*"):
        with open(mon_path / "name") as name:
            dev_path = mon_path.resolve().relative_to("/sys").parent.parent
            monitors.append(MonitorMapping(dev_path, mon_path.name, name.read().strip()))
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
