"""Generate the boss-facing 'Read Me First.pdf' instructions."""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, ListFlowable, ListItem,
    Table, TableStyle, PageBreak,
)
from reportlab.lib.enums import TA_LEFT

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "Read Me First.pdf"
LOGO = REPO / "assets" / "Provectus.jpg"

INDIGO = HexColor("#5e6ad2")
TEXT   = HexColor("#18181b")
MUTED  = HexColor("#71717a")
SUBTLE = HexColor("#f4f4f5")
BORDER = HexColor("#e7e7e9")

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Normal"],
                    fontName="Helvetica-Bold", fontSize=22, leading=26,
                    textColor=TEXT, spaceAfter=6)
EYEBROW = ParagraphStyle("EYEBROW", parent=styles["Normal"],
                         fontName="Helvetica-Bold", fontSize=9, leading=12,
                         textColor=MUTED, spaceAfter=3)
H2 = ParagraphStyle("H2", parent=styles["Normal"],
                    fontName="Helvetica-Bold", fontSize=14, leading=18,
                    textColor=TEXT, spaceBefore=18, spaceAfter=6)
BODY = ParagraphStyle("BODY", parent=styles["Normal"],
                      fontName="Helvetica", fontSize=11, leading=16,
                      textColor=TEXT, spaceAfter=8, alignment=TA_LEFT)
SMALL = ParagraphStyle("SMALL", parent=styles["Normal"],
                       fontName="Helvetica", fontSize=10, leading=14,
                       textColor=MUTED, spaceAfter=6)
STEP = ParagraphStyle("STEP", parent=styles["Normal"],
                      fontName="Helvetica", fontSize=11, leading=17,
                      textColor=TEXT, spaceAfter=4, leftIndent=4)


def callout(text: str, color=INDIGO) -> Table:
    p = Paragraph(text, ParagraphStyle("CALL", parent=BODY,
                                       fontSize=10.5, leading=15,
                                       textColor=TEXT))
    t = Table([[p]], colWidths=[6.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#eef0fb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def numbered(items: list) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(it, STEP), leftIndent=18, value=i + 1)
         for i, it in enumerate(items)],
        bulletType="1", start="1",
        leftIndent=12, bulletFontName="Helvetica-Bold",
        bulletColor=INDIGO, bulletFontSize=11,
    )


def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title="Provectus Analytics — Read Me First",
    )

    story = []

    # Logo
    if LOGO.exists():
        img = Image(str(LOGO), width=1.1 * inch, height=0.97 * inch)
        img.hAlign = "LEFT"
        story.append(img)
        story.append(Spacer(1, 14))

    story.append(Paragraph("GETTING STARTED", EYEBROW))
    story.append(Paragraph("Provectus Analytics", H1))
    story.append(Paragraph(
        "This is a small program that turns your Flight Schedule Pro reports "
        "into charts and tables — average cost per rating, hours per student, "
        "how long each rating takes, and so on. It runs entirely on your Mac. "
        "Nothing leaves your computer.", BODY))

    # ── Setup ──
    story.append(Paragraph("First time you open it", H2))
    story.append(numbered([
        "Find the <b>Provectus Analytics</b> folder you were given. "
        "(If it came as a zip file, double-click the zip first — it'll "
        "create the folder.)",
        "Open the folder. Inside, find a file called <b>Provectus.command</b>.",
        "<b>Right-click</b> on Provectus.command (or hold Control and click) → "
        "choose <b>Open</b> from the menu.",
        "Your Mac will show a warning that says something like "
        "<i>“Apple cannot check it for malicious software.”</i> "
        "Click <b>Open</b> anyway. (This only happens the first time.)",
        "A black Terminal window opens. It will say "
        "<i>“installing dependencies…”</i> for 1–2 minutes. This is normal.",
        "When it's done, your web browser opens automatically and shows the "
        "dashboard. You're in.",
    ]))

    story.append(callout(
        "<b>Important:</b> leave the Terminal window open while you use the "
        "dashboard. Closing it stops the program."))

    # ── Day to day ──
    story.append(Paragraph("Every other time", H2))
    story.append(Paragraph(
        "Just <b>double-click</b> Provectus.command. No right-click needed "
        "anymore. The browser opens to the dashboard in a few seconds.", BODY))

    # ── Quitting ──
    story.append(Paragraph("When you're done", H2))
    story.append(Paragraph(
        "Close the Terminal window. That's it. The browser tab can stay open — "
        "it just won't work until you launch the program again.", BODY))

    # ── Updating data ──
    story.append(PageBreak())
    story.append(Paragraph("Updating the data", H2))
    story.append(Paragraph(
        "The dashboard reads four spreadsheets from inside the "
        "<b>Provectus Analytics</b> folder. Each one comes from a different "
        "place:", BODY))

    data_rows = [
        ["File on your computer", "Comes from"],
        ["synthetic_fsp_clients.csv",
         "Flight Schedule Pro → Sales by Client"],
        ["synthetic_fsp_reservations.csv",
         "Flight Schedule Pro → Reservation Detail"],
        ["synthetic_fsp_invoices.csv",
         "Flight Schedule Pro → Invoice Detail"],
        ["synthetic_alumni_survey.csv",
         "Google Form → Responses → Download CSV"],
    ]
    t = Table(data_rows, colWidths=[2.6 * inch, 3.7 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
        ("BACKGROUND", (0, 0), (-1, 0), SUBTLE),
        ("LINEBELOW", (0, 0), (-1, 0), 1, BORDER),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("To replace the data:", BODY))
    story.append(numbered([
        "Download the new spreadsheets from FSP and the Google Form.",
        "Replace the four files inside the <b>Provectus Analytics</b> folder. "
        "Keep the exact same filenames.",
        "If the dashboard is open: in the dark sidebar on the left, click the "
        "<b>Rebuild DB</b> button. Then reload the browser tab.",
        "If the dashboard isn't open: just launch it again. It picks up the "
        "new files automatically.",
    ]))

    story.append(callout(
        "<b>Right now the files have “synthetic_” in their names</b> because "
        "they're test data. When real Provectus exports arrive, Olsen will "
        "either rename the files or update the program to use real names."))

    # ── Troubleshooting ──
    story.append(Paragraph("If something goes wrong", H2))

    trouble = [
        ("The browser didn't open.",
         "Open your browser yourself and type <b>127.0.0.1:8050</b> in the "
         "address bar."),
        ("The Mac says “Python 3 is not installed.”",
         "Install Python from <b>python.org/downloads/macos</b>, then try again."),
        ("The Terminal says “port already in use.”",
         "Another copy of the program is already running. Close the older "
         "Terminal window, then try again."),
        ("The dashboard shows the wrong numbers after I replaced the CSVs.",
         "Click <b>Rebuild DB</b> in the sidebar, then reload the page."),
        ("Anything else.",
         "Take a screenshot of the Terminal window and send it to Olsen — "
         "that's where errors show up."),
    ]
    for q, a in trouble:
        story.append(Paragraph(f"<b>{q}</b>", BODY))
        story.append(Paragraph(a, ParagraphStyle("A", parent=BODY,
                                                 leftIndent=12, spaceAfter=10)))

    # ── Switching themes ──
    story.append(Paragraph("Light mode and dark mode", H2))
    story.append(Paragraph(
        "Bottom of the dark sidebar, click the <b>Theme</b> button to toggle "
        "between light and dark. Your choice is remembered next time.", BODY))

    story.append(Spacer(1, 26))
    story.append(Paragraph(
        "Questions, anything broken, anything confusing — text Olsen.", SMALL))

    doc.build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
