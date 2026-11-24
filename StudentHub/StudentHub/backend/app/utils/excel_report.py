"""utils/excel_report.py — headers/rows -> a styled .xlsx workbook, used by every /reports Excel export."""
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


def build_table_excel(sheet_title: str, headers: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31] or "Report"

    header_fill = PatternFill("solid", fgColor="2563EB")
    header_font = Font(color="FFFFFF", bold=True)
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for r, row in enumerate(rows, start=2):
        for c, value in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=value if value is not None else "—")

    for col in range(1, len(headers) + 1):
        width = max([len(str(headers[col - 1]))] + [len(str(row[col - 1])) for row in rows if col - 1 < len(row)] + [8])
        ws.column_dimensions[get_column_letter(col)].width = min(width + 3, 40)
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
