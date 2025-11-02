"""Report task handler."""
from __future__ import annotations

import io
import textwrap
import zipfile
from typing import Tuple

REPORT_SQL = """SELECT project, SUM(amount) AS total_amount, COUNT(*) AS tasks
FROM source
group by project
order by total_amount desc;
"""

README = textwrap.dedent(
    """
    # Отчёт AIU-CORE

    1. Сырые данные читаются из `source.csv`.
    2. SQL-скрипт в `report.sql` агрегирует суммы и количество задач по проектам.
    3. Готовый отчёт доступен в `report.csv`.
    """
)

REPORT_CSV = """project,total_amount,tasks
Core,12000,4
Ops,8000,3
"""


async def generate_archive(order_id: str) -> Tuple[str, bytes]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("report.sql", REPORT_SQL)
        archive.writestr("README.md", README)
        archive.writestr("report.csv", REPORT_CSV)
    buffer.seek(0)
    filename = f"report-{order_id}.zip"
    return filename, buffer.getvalue()
