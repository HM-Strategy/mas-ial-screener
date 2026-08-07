from fpdf import FPDF
from datetime import datetime

BRAND_DARK = (26, 54, 109)
BRAND_BLUE = (59, 130, 246)
RED_FLAG = (196, 30, 58)
GREEN_CLEAN = (46, 125, 50)
AMBER = (245, 127, 23)
DARK_TEXT = (30, 41, 59)
GREY_TEXT = (100, 116, 139)
WHITE = (255, 255, 255)
LIGHT_BG = (240, 244, 248)

_ASCII_REPLACEMENTS = {
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
}


def _san(value) -> str:
    s = str(value)
    for k, v in _ASCII_REPLACEMENTS.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

DISCLAIMER = (
    "Generated automatically from MAS Investor Alert List. "
    "Preliminary check only. Does not constitute legal or compliance advice."
)


class MASReport(FPDF):
    def header(self):
        self.set_fill_color(*BRAND_DARK)
        self.rect(0, 0, 210, 22, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(10, 5)
        self.cell(0, 6, "HM Strategy", align="L")
        self.set_font("Helvetica", "", 8)
        self.set_xy(10, 12)
        self.cell(0, 5, "Compliance Screening Report", align="L")
        self.set_xy(10, 18)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 4, datetime.now().strftime("%d %b %Y"), align="L")
        self.line(10, 22, 200, 22)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*BRAND_BLUE)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY_TEXT)
        self.cell(0, 10, DISCLAIMER, align="L")
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")


def _confidence_color(confidence: int) -> tuple:
    if confidence == 100:
        return (46, 125, 50)
    elif confidence >= 90:
        return (245, 127, 23)
    return (230, 81, 0)


def _section_title(pdf: FPDF, title: str):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BRAND_DARK)
    pdf.cell(0, 10, title, align="L")
    pdf.ln(4)
    pdf.set_draw_color(*BRAND_BLUE)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(6)


def _info_box(pdf: FPDF, text: str, bg_color: tuple = LIGHT_BG):
    pdf.set_fill_color(*bg_color)
    pdf.set_draw_color(*BRAND_DARK)
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*DARK_TEXT)
    pdf.set_xy(12, y + 2)
    pdf.multi_cell(186, 7, _san(text), border=0, fill=True)
    pdf.set_y(pdf.get_y() + 4)


def _styled_table(pdf: FPDF, headers: list[str], rows: list[list],
                  col_widths: list[int], color_rows: bool = False,
                  confidence_idx: int | None = None):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_fill_color(*BRAND_DARK)
    pdf.set_text_color(*WHITE)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, _san(h), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for row_index, row in enumerate(rows):
        if color_rows and confidence_idx is not None:
            val = row[confidence_idx]
            if isinstance(val, str) and val.isdigit():
                val = int(val)
            r, g, b = _confidence_color(val if isinstance(val, int) else 0)
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(*WHITE)
            fill = True
        elif row_index % 2 == 0:
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_text_color(*DARK_TEXT)
            fill = True
        else:
            pdf.set_text_color(*DARK_TEXT)
            fill = False

        for i, cell in enumerate(row):
            pdf.cell(col_widths[i], 7, _san(cell), border=1, fill=fill)
        pdf.ln()
    pdf.set_text_color(*DARK_TEXT)


def _generate_matches_table(matches: list[dict]) -> tuple:
    if not matches:
        return [], [], []
    headers = ["Client Name", "Matched Alert", "Confidence", "Match Type", "Type", "Date Added"]
    widths = [44, 44, 18, 18, 32, 30]
    rows = [
        [
            m["client_name"][:40],
            m["matched_entry"]["name"][:40],
            str(m["confidence"]),
            m["match_type"].upper(),
            m["matched_entry"]["type"][:30],
            m["matched_entry"]["date_added"],
        ]
        for m in matches
    ]
    return headers, widths, rows


def generate_notification_report(new_entries: list[dict], client_matches: list[dict]) -> bytes:
    pdf = MASReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    _section_title(pdf, "New Entries Notification")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(0, 8, f"{len(new_entries)} new entr{'y' if len(new_entries) == 1 else 'ies'} found on the MAS Investor Alert List")
    pdf.ln(10)

    if client_matches:
        pdf.set_draw_color(*RED_FLAG)
        pdf.set_line_width(1)
        pdf.line(10, pdf.get_y(), 12, pdf.get_y())
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*RED_FLAG)
        pdf.cell(0, 8, f"  {len(client_matches)} client(s) flagged - review required")
        pdf.ln(12)
        pdf.set_text_color(*DARK_TEXT)

        mh, mw, mr = _generate_matches_table(client_matches)
        _styled_table(pdf, mh, mr, mw, color_rows=True, confidence_idx=2)

        pdf.ln(8)

    new_headers = ["#", "Name", "Aliases", "Type", "Date Added"]
    new_widths = [8, 62, 52, 42, 28]
    new_rows = [
        [str(i + 1), e["name"][:60], ", ".join(e["aliases"])[:50],
         e["type"][:40], e["date_added"]]
        for i, e in enumerate(new_entries)
    ]
    _styled_table(pdf, new_headers, new_rows, new_widths)

    return bytes(pdf.output())


def generate_screening_report(matches: list[dict], total_screened: int) -> bytes:
    pdf = MASReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    _section_title(pdf, "Client Screening Report")

    if not matches:
        pdf.set_fill_color(*GREEN_CLEAN)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 12)
        y = pdf.get_y()
        pdf.rect(10, y, 190, 20, "F")
        pdf.set_xy(12, y + 3)
        pdf.cell(186, 7, f"{total_screened} clients screened - No matches found", align="C")
        pdf.set_xy(12, y + 11)
        pdf.cell(186, 7, "All names are clear.", align="C")
        pdf.set_y(y + 24)
        pdf.set_text_color(*DARK_TEXT)
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*DARK_TEXT)
        pdf.cell(0, 8, f"{total_screened} clients screened, {len(matches)} potential match(es) found")
        pdf.ln(14)

        mh, mw, mr = _generate_matches_table(matches)
        _styled_table(pdf, mh, mr, mw, color_rows=True, confidence_idx=2)

    return bytes(pdf.output())


def generate_single_search_report(result: dict) -> bytes:
    pdf = MASReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    _section_title(pdf, "Individual Search Report")

    name = result.get("client_name", "")
    flagged = result.get("match", False)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(0, 8, _san(f"Searched entity:  {name}"))
    pdf.ln(14)

    if flagged:
        entry = result.get("matched_entry", {})
        pdf.set_fill_color(*RED_FLAG)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 12)
        pdf.rect(10, pdf.get_y(), 190, 14, "F")
        pdf.set_xy(15, pdf.get_y() + 3)
        pdf.cell(0, 8, "FLAGGED - Potential match found", align="L")
        pdf.set_y(pdf.get_y() + 18)
        pdf.set_text_color(*DARK_TEXT)

        details = [
            ("Matched Alert", entry.get("name", "")),
            ("Confidence", f'{result.get("confidence", 0)}% ({result.get("match_type", "").upper()})'),
            ("Type", entry.get("type", "")),
            ("Date Added", entry.get("date_added", "")),
            ("Aliases", ", ".join(entry.get("aliases", [])) or "None"),
        ]
        for label, value in details:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*GREY_TEXT)
            pdf.cell(45, 8, _san(label), align="L")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK_TEXT)
            pdf.cell(0, 8, _san(value), align="L")
            pdf.ln(8)
    else:
        pdf.set_fill_color(*GREEN_CLEAN)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 12)
        y = pdf.get_y()
        pdf.rect(10, y, 190, 14, "F")
        pdf.set_xy(15, y + 3)
        pdf.cell(0, 8, "NOT FLAGGED - Name is clear", align="L")

    return bytes(pdf.output())
