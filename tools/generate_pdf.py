import os
from pathlib import Path
from fpdf import FPDF

# Brand colour (RGB)
BRAND    = (26, 58, 107)
BRAND_BG = (232, 237, 247)
MUTED    = (100, 100, 110)
LIGHT    = (248, 249, 252)
DARK     = (26, 26, 46)

FONTS_DIR = Path(__file__).parent.parent / "fonts"

TRANSLATIONS = {
    "en": {
        "invoice":       "INVOICE",
        "invoice_num":   "Invoice #:",
        "date":          "Date:",
        "due_date":      "Due Date:",
        "bill_to":       "BILL TO",
        "description":   "Description",
        "qty":           "Qty",
        "unit_price":    "Unit Price",
        "amount":        "Amount",
        "subtotal":      "Subtotal",
        "vat":           "VAT",
        "total_due":     "Total Due",
        "notes_title":   "NOTES & PAYMENT TERMS",
        "footer_thanks": "Thank you for your business",
        "vat_reg":       "VAT Reg:",
    },
    "fr": {
        "invoice":       "FACTURE",
        "invoice_num":   "Facture :",
        "date":          "Date :",
        "due_date":      "Échéance :",
        "bill_to":       "FACTURER À",
        "description":   "Description",
        "qty":           "Qté",
        "unit_price":    "Prix Unitaire",
        "amount":        "Montant",
        "subtotal":      "Sous-total",
        "vat":           "TVA",
        "total_due":     "Total TTC",
        "notes_title":   "NOTES & CONDITIONS DE PAIEMENT",
        "footer_thanks": "Merci de votre confiance",
        "vat_reg":       "N° TVA :",
    },
}


class InvoicePDF(FPDF):
    def __init__(self, company: dict, language: str = "en"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.company = company
        self.language = language
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)
        # Register Arial with Unicode support (includes € and other symbols)
        self.add_font("Arial", style="",  fname=str(FONTS_DIR / "Arial.ttf"))
        self.add_font("Arial", style="B", fname=str(FONTS_DIR / "Arial-Bold.ttf"))

    def footer(self):
        t = TRANSLATIONS.get(self.language, TRANSLATIONS["en"])
        self.set_y(-14)
        self.set_font("Arial", size=7)
        self.set_text_color(*MUTED)
        text = (
            f"{self.company['name']}  ·  {t['vat_reg']} {self.company['vat']}"
            f"  ·  {self.company['email']}  ·  {t['footer_thanks']}"
        )
        self.cell(0, 6, text, align="C")


def generate_invoice_pdf(invoice_data: dict, company: dict, language: str = "en") -> bytes:
    t = TRANSLATIONS.get(language, TRANSLATIONS["en"])

    pdf = InvoicePDF(company, language=language)
    pdf.add_page()

    page_w = pdf.w - pdf.l_margin - pdf.r_margin  # usable width

    # ── Header ──────────────────────────────────────────────────────────────
    logo_path = company.get("logo_path", "")
    logo_rendered = False

    if logo_path and os.path.exists(logo_path):
        try:
            ext = os.path.splitext(logo_path)[1].lower()
            logo_max_h = 18  # mm — matches company info block height
            if ext == ".svg":
                from fpdf.svg import SVGObject
                svg = SVGObject.from_file(logo_path)
                aspect = float(svg.height) / float(svg.width) if svg.width else 1
                logo_h = logo_max_h
                logo_w = logo_h / aspect
                pdf.image(logo_path, x=pdf.l_margin, y=pdf.t_margin, w=logo_w)
                # fpdf2 doesn't advance Y after SVG — do it manually
                pdf.set_y(pdf.t_margin + logo_h)
            else:
                logo_w = logo_max_h / 1.0  # square fallback; raster uses explicit h
                pdf.image(logo_path, x=pdf.l_margin, y=pdf.t_margin, w=logo_w, h=logo_max_h)
                pdf.set_y(pdf.t_margin + logo_max_h)
            logo_rendered = True
        except Exception:
            logo_rendered = False

    if not logo_rendered:
        pdf.set_font("Arial", style="B", size=16)
        pdf.set_text_color(*BRAND)
        pdf.cell(0, 10, company["name"], ln=True)

    # Company info block (top-right)
    info_x = pdf.l_margin + page_w - 75
    pdf.set_xy(info_x, pdf.t_margin)
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(*MUTED)
    for line in [
        company["address"],
        company["email"],
        company["phone"],
        f"{t['vat_reg']} {company['vat']}",
    ]:
        pdf.set_x(info_x)
        pdf.cell(75, 4.5, line, align="R", ln=True)

    # Divider line
    y_after_header = max(pdf.get_y(), pdf.t_margin + 20)
    pdf.set_draw_color(*BRAND)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, y_after_header + 3, pdf.l_margin + page_w, y_after_header + 3)
    pdf.ln(7)

    # ── Invoice title + meta ─────────────────────────────────────────────────
    y_section = pdf.get_y()

    # Left: big title
    pdf.set_font("Arial", style="B", size=26)
    pdf.set_text_color(*BRAND)
    pdf.set_xy(pdf.l_margin, y_section)
    pdf.cell(100, 14, t["invoice"], ln=False)

    # Right: meta box
    meta_x = pdf.l_margin + page_w - 70
    meta_y = y_section
    box_h  = 24
    pdf.set_fill_color(*BRAND_BG)
    pdf.rect(meta_x, meta_y, 70, box_h, style="F")

    pdf.set_font("Arial", size=8)
    pdf.set_text_color(*MUTED)
    rows = [
        (t["invoice_num"], invoice_data["invoice_number"]),
        (t["date"],        invoice_data["invoice_date"]),
        (t["due_date"],    invoice_data["due_date"]),
    ]
    pdf.set_xy(meta_x + 3, meta_y + 3)
    for label, value in rows:
        pdf.set_x(meta_x + 3)
        pdf.set_font("Arial", style="B", size=8)
        pdf.set_text_color(*MUTED)
        pdf.cell(24, 6, label)
        pdf.set_font("Arial", style="B", size=8)
        pdf.set_text_color(*DARK)
        pdf.cell(40, 6, value, ln=True)

    pdf.set_xy(pdf.l_margin, y_section + box_h + 6)

    # ── Bill To ──────────────────────────────────────────────────────────────
    bt_y = pdf.get_y()
    pdf.set_fill_color(*BRAND)
    pdf.rect(pdf.l_margin, bt_y, page_w, 7, style="F")
    pdf.set_font("Arial", style="B", size=7)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(pdf.l_margin + 3, bt_y + 1.5)
    pdf.cell(0, 4, t["bill_to"], ln=True)

    pdf.set_fill_color(*LIGHT)
    bt_body_y = bt_y + 7
    bt_body_h  = 22
    pdf.rect(pdf.l_margin, bt_body_y, page_w, bt_body_h, style="F")

    pdf.set_xy(pdf.l_margin + 4, bt_body_y + 3)
    pdf.set_font("Arial", style="B", size=10)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 5, invoice_data["customer_name"], ln=True)

    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Arial", size=8.5)
    pdf.set_text_color(*MUTED)
    address_lines = invoice_data["customer_address"].replace("\r", "").split("\n")
    address_lines.append(invoice_data["customer_email"])
    for addr_line in address_lines:
        pdf.set_x(pdf.l_margin + 4)
        pdf.cell(0, 4.5, addr_line, ln=True)

    pdf.set_y(bt_body_y + bt_body_h + 8)

    # ── Line items table ─────────────────────────────────────────────────────
    col_w   = [page_w * 0.50, page_w * 0.13, page_w * 0.18, page_w * 0.19]
    headers = [t["description"], t["qty"], t["unit_price"], t["amount"]]
    aligns  = ["L", "R", "R", "R"]

    # Table header
    th_y = pdf.get_y()
    pdf.set_fill_color(*BRAND)
    pdf.rect(pdf.l_margin, th_y, page_w, 8, style="F")
    pdf.set_font("Arial", style="B", size=8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(pdf.l_margin, th_y)
    for i, (hdr, w, al) in enumerate(zip(headers, col_w, aligns)):
        x_off = 3 if i == 0 else 0
        pdf.cell(w, 8, hdr, align=al, border=0)
    pdf.ln()

    # Rows
    pdf.set_font("Arial", size=9)
    for idx, item in enumerate(invoice_data["line_items"]):
        row_y = pdf.get_y()
        fill  = idx % 2 == 1
        if fill:
            pdf.set_fill_color(*LIGHT)
            pdf.rect(pdf.l_margin, row_y, page_w, 8, style="F")

        line_total = item["quantity"] * item["unit_price"]
        values = [
            item["description"],
            str(int(item["quantity"]) if item["quantity"] == int(item["quantity"]) else item["quantity"]),
            f'€{item["unit_price"]:.2f}',
            f'€{line_total:.2f}',
        ]
        pdf.set_text_color(*DARK)
        pdf.set_xy(pdf.l_margin, row_y)
        for i, (val, w, al) in enumerate(zip(values, col_w, aligns)):
            x_off = 3 if i == 0 else 0
            if i == 0:
                pdf.cell(w, 8, val, align=al, border=0)
            else:
                pdf.cell(w, 8, val, align=al, border=0)
        pdf.ln()

        # Bottom border
        pdf.set_draw_color(220, 225, 235)
        pdf.set_line_width(0.2)
        row_bottom = pdf.get_y()
        pdf.line(pdf.l_margin, row_bottom, pdf.l_margin + page_w, row_bottom)

    pdf.ln(4)

    # ── Totals ───────────────────────────────────────────────────────────────
    totals_x = pdf.l_margin + page_w - 75
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(*MUTED)

    def totals_row(label, value, bold=False, large=False):
        pdf.set_x(totals_x)
        sz = 11 if large else 9
        style = "B" if bold or large else ""
        pdf.set_font("Arial", style=style, size=sz)
        pdf.set_text_color(*DARK if bold or large else MUTED)
        pdf.cell(40, 7, label)
        pdf.set_text_color(*DARK)
        pdf.cell(35, 7, value, align="R", ln=True)

    totals_row(t["subtotal"], f'€{invoice_data["subtotal"]:.2f}')
    totals_row(f'{t["vat"]} ({invoice_data["vat_rate"]}%)', f'€{invoice_data["vat_amount"]:.2f}')

    # Grand total divider
    gt_y = pdf.get_y() + 1
    pdf.set_draw_color(*BRAND)
    pdf.set_line_width(0.5)
    pdf.line(totals_x, gt_y, totals_x + 75, gt_y)
    pdf.ln(2)

    totals_row(t["total_due"], f'€{invoice_data["total"]:.2f}', bold=True, large=True)

    # ── Notes ────────────────────────────────────────────────────────────────
    notes = (invoice_data.get("notes") or "").strip()
    if notes:
        pdf.ln(6)
        pdf.set_draw_color(220, 225, 235)
        pdf.set_line_width(0.3)
        n_y = pdf.get_y()
        pdf.line(pdf.l_margin, n_y, pdf.l_margin + page_w, n_y)
        pdf.ln(4)

        pdf.set_font("Arial", style="B", size=7)
        pdf.set_text_color(*BRAND)
        pdf.cell(0, 5, t["notes_title"], ln=True)
        pdf.set_font("Arial", size=8.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(page_w, 5, notes)

    return bytes(pdf.output())
