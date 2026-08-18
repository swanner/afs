from __future__ import annotations

from .application import Application
from .unit import AFS_TEMPLATE_01_UNIT


def build_application() -> tuple[Application, AFS_TEMPLATE_01_UNIT]:
    app = Application()

    # AFS PATTERN: Integration is explicit and visible. Search & Replace of
    # AFS_TEMPLATE_01_UNIT also finds this registration point.
    unit = AFS_TEMPLATE_01_UNIT(target=3)
    app.add_unit(unit)

    return app, unit


def main() -> int:
    app, unit = build_application()
    app.run(scans=10)

    status = unit.status
    print(
        f"{status.name}: state={status.state.name} "
        f"value={status.value} alarm={status.alarm or 'none'}"
    )
    return 0
