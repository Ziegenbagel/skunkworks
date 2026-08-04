from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Skunkworks_Operator_Manual.docx"
FIGURE = ROOT / "assets" / "mission-control-dashboard-numbered.png"
SETTINGS_FIGURE = ROOT / "assets" / "settings-workspace-numbered.png"
WORKSPACE_ASSETS = ROOT / "assets" / "workspace-diagrams"
DEFAULT_SCREENSHOT = Path("/Users/ziegenbagel/Documents/Screenshot 2026-08-01 at 1.12.30 AM.png")
SCREENSHOT = Path(os.environ.get("SKUNKWORKS_GUIDE_SCREENSHOT", DEFAULT_SCREENSHOT))
DEFAULT_SETTINGS_SCREENSHOT = Path("/Users/ziegenbagel/Documents/Screenshot 2026-07-31 at 11.18.11 PM.png")
SETTINGS_SCREENSHOT = Path(os.environ.get("SKUNKWORKS_GUIDE_SETTINGS_SCREENSHOT", DEFAULT_SETTINGS_SCREENSHOT))

NAVY = RGBColor(5, 23, 34)
CYAN = RGBColor(0, 196, 220)
BLUE = RGBColor(27, 105, 145)
MUTED = RGBColor(91, 111, 123)
AMBER = RGBColor(180, 121, 0)
RED = RGBColor(165, 38, 45)
LIGHT = RGBColor(232, 238, 245)


def font(run, size=11, bold=False, color=NAVY, name="Aptos"):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_width(cell, dxa):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(dxa))
    tc_w.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_w.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            set_cell_width(cell, width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    return p


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.25
    if bold_lead and text.startswith(bold_lead):
        font(p.add_run(bold_lead), bold=True)
        font(p.add_run(text[len(bold_lead):]))
    else:
        font(p.add_run(text))
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Inches(0.375)
        p.paragraph_format.first_line_indent = Inches(-0.188)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.25
        font(p.add_run(item))


def add_steps(doc, items):
    numbering = doc.part.numbering_part.element
    abstract_ids = [int(node.get(qn("w:abstractNumId"))) for node in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(node.get(qn("w:numId"))) for node in numbering.findall(qn("w:num"))]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    for tag, value in (("w:start", "1"), ("w:numFmt", "decimal"), ("w:lvlText", "%1."), ("w:lvlJc", "right")):
        element = OxmlElement(tag)
        element.set(qn("w:val"), value)
        level.append(element)
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    p_pr.append(tabs)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "540")
    indent.set(qn("w:hanging"), "270")
    p_pr.append(indent)
    level.append(p_pr)
    abstract.append(level)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)

    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.25
        num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
        ilvl = OxmlElement("w:ilvl")
        ilvl.set(qn("w:val"), "0")
        num_pr.append(ilvl)
        num_id_element = OxmlElement("w:numId")
        num_id_element.set(qn("w:val"), str(num_id))
        num_pr.append(num_id_element)
        font(p.add_run(item))


def add_note(doc, title, text, severity="note"):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    fill = "FFF4D6" if severity == "warning" else "E8EEF5"
    shade(table.cell(0, 0), fill)
    p = table.cell(0, 0).paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    font(p.add_run(title.upper() + "  "), bold=True, color=AMBER if severity == "warning" else BLUE)
    font(p.add_run(text))
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def make_dashboard_figure():
    if not SCREENSHOT.exists():
        return False
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(SCREENSHOT).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except OSError:
        label_font = ImageFont.load_default()
    # Coordinates are fractions so the overlay survives normal window-size changes.
    points = [
        (0.085, 0.165), (0.750, 0.120), (0.515, 0.166), (0.505, 0.425),
        (0.087, 0.280), (0.088, 0.500), (0.087, 0.720), (0.560, 0.775),
        (0.405, 0.895), (0.725, 0.895),
    ]
    radius = max(20, image.width // 70)
    for number, (xf, yf) in enumerate(points, 1):
        x, y = int(image.width * xf), int(image.height * yf)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(0, 196, 220, 235), outline=(255, 255, 255, 255), width=3)
        text = str(number)
        box = draw.textbbox((0, 0), text, font=label_font)
        draw.text((x-(box[2]-box[0])/2, y-(box[3]-box[1])/2-2), text, font=label_font, fill=(0, 15, 24, 255))
    image.convert("RGB").save(FIGURE, quality=94)
    return True


def make_settings_figure():
    if not SETTINGS_SCREENSHOT.exists():
        return False
    SETTINGS_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(SETTINGS_SCREENSHOT).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except OSError:
        label_font = ImageFont.load_default()
    points = [
        (0.12, 0.31), (0.13, 0.51), (0.13, 0.55), (0.29, 0.59),
        (0.49, 0.70), (0.18, 0.88), (0.39, 0.88), (0.67, 0.88),
    ]
    radius = max(20, image.width // 70)
    for number, (xf, yf) in enumerate(points, 1):
        x, y = int(image.width * xf), int(image.height * yf)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(0, 196, 220, 235), outline=(255, 255, 255, 255), width=3)
        text = str(number)
        box = draw.textbbox((0, 0), text, font=label_font)
        draw.text((x-(box[2]-box[0])/2, y-(box[3]-box[1])/2-2), text, font=label_font, fill=(0, 15, 24, 255))
    image.convert("RGB").save(SETTINGS_FIGURE, quality=94)
    return True


def make_workspace_diagram(key, title, zones):
    """Create a clean, manual-style schematic when a live screenshot would date quickly."""
    path = WORKSPACE_ASSETS / f"{key}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 820), (4, 18, 28))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 25)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 19)
    except OSError:
        title_font = label_font = small_font = ImageFont.load_default()
    draw.rectangle((22, 22, 1578, 798), outline=(0, 196, 220), width=3)
    draw.text((55, 45), title.upper(), font=title_font, fill=(232, 238, 245))
    draw.text((55, 95), "SCHEMATIC CONTROL MAP · LIVE VALUES AND BUTTON AVAILABILITY VARY", font=small_font, fill=(91, 150, 170))
    columns = 2 if len(zones) <= 6 else 3
    rows = (len(zones) + columns - 1) // columns
    x_gap, y_gap = 30, 24
    left, top, right, bottom = 55, 145, 1545, 750
    cell_w = (right - left - x_gap * (columns - 1)) // columns
    cell_h = (bottom - top - y_gap * (rows - 1)) // rows
    for index, (name, detail) in enumerate(zones, 1):
        offset = index - 1
        column, row = offset % columns, offset // columns
        x = left + column * (cell_w + x_gap)
        y = top + row * (cell_h + y_gap)
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=14, fill=(10, 38, 53), outline=(28, 96, 118), width=3)
        draw.ellipse((x + 18, y + 18, x + 66, y + 66), fill=(0, 196, 220), outline=(232, 238, 245), width=2)
        number = str(index)
        box = draw.textbbox((0, 0), number, font=label_font)
        draw.text((x + 42 - (box[2]-box[0])/2, y + 42 - (box[3]-box[1])/2 - 2), number, font=label_font, fill=(4, 18, 28))
        draw.text((x + 82, y + 18), name.upper(), font=label_font, fill=(232, 238, 245))
        draw.multiline_text((x + 24, y + 82), detail, font=small_font, fill=(145, 173, 188), spacing=7)
    image.save(path, quality=94)
    return path


def add_workspace_diagram(doc, key, title, zones):
    path = make_workspace_diagram(key, title, zones)
    doc.add_picture(str(path), width=Inches(6.7))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption = doc.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font(caption.add_run(f"Control diagram · {title}."), size=9, color=MUTED)


def add_dashboard_legend(doc):
    rows = [
        ("1", "System status", "Overall readiness and current findings."),
        ("2", "Focused probe", "Selects which probe supplies sector, resource, navigation, and fleet context."),
        ("3", "Primary navigation", "Opens Mission Control, Fleet, Galaxy Map, Navigation, Resources, Missions, Production, Safety, Logbook, and Settings."),
        ("4", "Live sector view", "Star-centered schematic with planets, asteroids, probes, relays, and grouped Manny activity."),
        ("5", "Fleet status", "Fleet totals and operational/active/critical posture."),
        ("6", "Resource summary", "Focused-probe fuel percentage and accessible resource quantities."),
        ("7", "Safety overview", "Highest-priority safety state and plain-language reason."),
        ("8", "Active alerts", "Warnings and critical conditions; open the full Safety view for details."),
        ("9", "Active missions", "A compact summary; click for the full mission list."),
        ("10", "Production queue", "Current crafting, assembly, and mining work; click for full details."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    set_table_geometry(table, [600, 2150, 6610])
    for i, label in enumerate(("No.", "Control", "Purpose")):
        shade(table.rows[0].cells[i], "E8EEF5")
        font(table.rows[0].cells[i].paragraphs[0].add_run(label), bold=True, color=BLUE)
    for number, control, purpose in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, (number, control, purpose)):
            font(cell.paragraphs[0].add_run(text), size=9.5)
        set_table_geometry(table, [600, 2150, 6610])


def add_settings_legend(doc):
    rows = [
        ("1", "Account & API credential", "Secure API-key storage, connection testing, removal, and first-launch walkthrough."),
        ("2", "Automation execution", "Explains the current command mode and its safety boundaries."),
        ("3", "Execution mode", "Observe Only, Require Approval, or Automatic."),
        ("4", "Command allowlist", "Limits which crafting, mining, and travel command families may be sent."),
        ("5", "Proposed command queue", "Shows actionable work or the reason nothing can currently run."),
        ("6", "Automation target", "The object or reserve Skunkworks should maintain."),
        ("7", "Desired quantity", "How many completed objects or how much reserve should exist."),
        ("8", "Priority", "Importance from 1–10; 1 is highest and equal values share priority."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    set_table_geometry(table, [600, 2450, 6310])
    for i, label in enumerate(("No.", "Settings area", "Purpose")):
        shade(table.rows[0].cells[i], "E8EEF5")
        font(table.rows[0].cells[i].paragraphs[0].add_run(label), bold=True, color=BLUE)
    for number, area, purpose in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, (number, area, purpose)):
            font(cell.paragraphs[0].add_run(text), size=9.3)
        set_table_geometry(table, [600, 2450, 6310])


def build():
    has_figure = make_dashboard_figure()
    has_settings_figure = make_settings_figure()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.72)
    section.left_margin = section.right_margin = Inches(0.8)
    section.header_distance = section.footer_distance = Inches(0.4)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    for name, size, before, after, color in (
        ("Heading 1", 16, 18, 10, CYAN),
        ("Heading 2", 13, 14, 7, BLUE),
        ("Heading 3", 12, 10, 5, NAVY),
    ):
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    font(header.add_run("SKUNKWORKS  |  OPERATOR MANUAL  |  v0.2"), size=8, bold=True, color=MUTED)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font(footer.add_run("Autonomous Exploration & Fleet Operations  •  Updated 2026-08-03"), size=8, color=MUTED)

    # Editorial-cover opening, adapted to the Skunkworks visual language.
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(80)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font(p.add_run("S K U N K W O R K S"), size=28, bold=True, color=NAVY, name="Aptos Display")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font(p.add_run("OPERATOR MANUAL"), size=18, bold=True, color=CYAN, name="Aptos Display")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(28)
    font(p.add_run("Mission Control, fleet automation, navigation, resources, and safety"), size=12, color=MUTED)
    if has_figure:
        doc.add_picture(str(FIGURE), width=Inches(6.7))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_note(doc, "Edition", "Version 0.2 is the living manual for the current development build. Screens and capabilities will be revised with the application.")
    doc.add_page_break()

    add_heading(doc, "1. Read This First")
    add_body(doc, "Skunkworks is a command-and-awareness layer for Von Neumann Game. It combines live account data, locally retained discoveries, planning, safety review, and optional automation. The focused probe determines the operational context shown across most screens.")
    add_note(doc, "Command authority", "Observe Only never sends game orders. Approval requires confirmation. Automatic can send allowlisted orders when live execution is enabled. The emergency stop overrides every mode.", "warning")
    add_heading(doc, "First launch", 2)
    add_steps(doc, [
        "Open Settings and enter the game API key. Skunkworks stores it in the operating-system credential vault, not in its settings file or logs.",
        "Use Test Connection and confirm that the network status becomes Connected.",
        "Select each probe from the Focused Probe menu and verify its name, model, status, sector, and fuel.",
        "Keep automation in Observe Only while reviewing the dashboard, maps, resources, and proposed command queue.",
        "Choose an execution mode and command allowlist only after the proposed work matches your intent.",
    ])
    add_heading(doc, "Status language", 2)
    add_bullets(doc, [
        "Nominal / Ready — no warning or critical condition was found. Informational notices may still reduce the readiness score slightly.",
        "Degraded — operation can continue, but at least one warning-level resource, data-quality, or safety condition needs attention.",
        "Warning — review is recommended before issuing a related command.",
        "Critical — a serious hazard or stop condition is present.",
        "Unknown — the API or local scan history does not contain enough information to make a reliable claim.",
    ])
    add_note(doc, "Notices versus health", "A notice such as every Manny currently being occupied remains visible, but it does not by itself mark the entire system Degraded. Open Safety or the finding details to see what affected the readiness score.")

    doc.add_page_break()
    add_heading(doc, "2. Mission Control Dashboard")
    add_body(doc, "The dashboard is an overview, not a replacement for the detailed workspaces. Its panels summarize the focused probe and fleet; clicking Active Missions, Production Queue, or Alerts opens the corresponding detailed view.")
    if has_figure:
        doc.add_picture(str(FIGURE), width=Inches(6.7))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font(caption.add_run("Figure 2-1. Mission Control dashboard and primary controls."), size=9, color=MUTED)
    add_dashboard_legend(doc)

    doc.add_page_break()
    add_heading(doc, "3. Focused Probe and Fleet")
    add_heading(doc, "Changing operational context", 2)
    add_steps(doc, [
        "Open Focused Probe in the top-right header.",
        "Choose a probe. Skunkworks loads that probe’s authoritative snapshot before replacing the dashboard context.",
        "Confirm the displayed sector, fuel, resources, and sector objects changed to the selected probe.",
        "Use Refresh if the game was changed in another window or the snapshot is stale.",
    ])
    add_note(doc, "Avoid stale assumptions", "A probe name changing immediately does not prove its sector snapshot has loaded. Wait for refresh completion and verify the FCC coordinates.", "warning")
    add_heading(doc, "Fleet workspace", 2)
    add_bullets(doc, [
        "Review every probe, including idle and unreachable probes.",
        "Rename a probe when the game API permits it.",
        "Assign an operational role such as hub, miner, transport, tanker reserve, explorer, or builder support.",
        "Treat roles as Skunkworks planning instructions; they do not change the physical probe model.",
    ])
    add_workspace_diagram(doc, "fleet", "Fleet workspace", [
        ("Focused probe identity", "Rename the selected probe and confirm its model and sector."),
        ("Manual repair", "Choose an idle Manny and the integrity percentage to restore."),
        ("Manual upgrade", "Choose an unlocked unfinished improvement and an idle Manny."),
        ("Fleet cards", "Select a probe card to reload the entire operational context."),
    ])
    add_note(doc, "Manny service interval", "Change the oil in your Manny every 3,000 ECE mined, or the completely imaginary warranty department may look sternly in your direction.")

    add_heading(doc, "4. Sector and Galaxy Maps")
    add_heading(doc, "Live sector view", 2)
    add_body(doc, "The sector view is star-centered. One orbital line is shown for each known planet, and planets are placed on their corresponding line. Asteroids, relays, probes, and containers occupy schematic positions because the game API does not expose precise real-time orbital coordinates.")
    add_bullets(doc, [
        "Mannys mining a known asteroid are grouped at that asteroid.",
        "Large Manny populations are summarized with counts to prevent the map from overflowing.",
        "Unknown or incomplete scans must remain visibly identified as uncertain.",
    ])
    add_heading(doc, "Galaxy map", 2)
    add_body(doc, "The galaxy map uses FCC X/Y/Z coordinates and initially centers its camera on the focused probe's current sector. Left-drag to rotate, right- or middle-drag to pan, and use the wheel to zoom. The pan arrow buttons provide precise movement, while Center Probe restores the focused-sector view. Lines represent verified neighboring-sector relationships. Select a sector dot to open its detail panel.")
    add_note(doc, "Local knowledge", "Detailed sector history is retained by Skunkworks after scans. A sector cannot display information the game API never exposed or Skunkworks never observed.")
    add_workspace_diagram(doc, "galaxy", "Galaxy map", [
        ("Sector details", "Click a dot to inspect FCC coordinates, knowledge, objects, and scan age."),
        ("Camera controls", "Rotate, pan, zoom, choose an axis view, or center the focused probe."),
        ("Map filters", "Filter discovery state, hazards, resources, containers, and recent travel."),
        ("Network lines", "Verified neighboring links and the focused probe's recent trail."),
    ])

    doc.add_page_break()
    add_heading(doc, "5. Navigation and Scanning")
    add_heading(doc, "Manual travel", 2)
    add_steps(doc, [
        "Select the probe that will travel.",
        "Enter destination FCC coordinates or choose a discovered sector.",
        "Preview the route and review deuterium, distance, cargo-detachment, and destination-refueling warnings.",
        "Confirm the command only after the displayed return or recovery plan is acceptable.",
    ])
    add_workspace_diagram(doc, "navigation-manual", "Navigation · Manual Travel", [
        ("Destination", "Enter FCC X, Y, and Z or select a known neighboring sector."),
        ("Route mode", "Choose direct or segmented routing before previewing."),
        ("Safety preview", "Review fuel, range, cargo, and destination-source findings."),
        ("Confirm", "Acknowledge displayed risk and send or cancel the movement order."),
    ])
    add_heading(doc, "Autonomous transport routes", 2)
    add_body(doc, "Transport routes define separate loading and unloading sectors, resource type, loading target, unloading threshold, return behavior, and a protected deuterium floor. Tanker unloading prefers a designated in-sector reserve tanker before filling a general probe when that policy is configured.")
    add_workspace_diagram(doc, "navigation-transport", "Navigation · Autonomous Transport", [
        ("Probe and resource", "Select the transport probe and the cargo or deuterium resource."),
        ("Loading sector", "Set the pickup FCC and fill target."),
        ("Unloading sector", "Set delivery FCC and empty-to percentage."),
        ("Return and fuel", "Choose return behavior and protect enough deuterium for the route."),
    ])
    add_heading(doc, "Scanning", 2)
    add_bullets(doc, [
        "Scan one adjacent sector when you need a specific observation.",
        "Scan All 12 Neighboring Sectors mirrors the game’s neighborhood scan and saves the available results.",
        "An exploration-role probe can automatically request the neighborhood scan after arriving in a new sector when exploration automation is enabled.",
        "SCUT coverage indicates communication reach; it does not guarantee a detailed scan already exists.",
    ])
    add_workspace_diagram(doc, "navigation-scan", "Navigation · Scanning & SCUT", [
        ("Neighbor list", "Shows 12 adjacent FCC sectors and their current knowledge state."),
        ("SCUT coverage", "Indicates whether each sector is in communication range."),
        ("Single scan", "Request the best available observation for one sector."),
        ("Scan all 12", "Observe every neighbor in one game-supported request."),
    ])

    add_heading(doc, "6. Resources and Inventory")
    add_body(doc, "Resources are grouped by where they exist: focused-probe storage, drifting containers, placed containers when exposed by the API, and remaining asteroid contents from the latest detailed scan. Equipment and constructed items must remain visible alongside bulk resources.")
    add_body(doc, "The Inventory & Containers page also provides manual controls for stock moves, resource or item jettison, container deployment to space, asteroids, or planets, detached-object recovery, same-sector deuterium transfer, and Manny reassignment. Live jettison, deployment, recovery, fuel transfer, and reassignment orders require confirmation. A container with space reserved for active crafting output cannot be detached, dropped, transferred, or emptied until that craft completes or is cancelled; the game enforces this reservation and Skunkworks preserves its explanatory error.")
    add_note(doc, "Container operations", "A Manny can recover drifting or detected asteroid-hidden containers. Whole containers can transfer directly to another owned probe in the same sector. Individual items still use jettison and salvage. Planet deployment consumes an Atmospheric Drop Kit, and transferring a busy Manny cancels its active task.")
    add_body(doc, "A manual mining order can deliver to the probe or a selected detached container. Probe delivery follows saved routing rules: a container assigned to the mined resource is preferred before unassigned storage. Automatic remote mining likewise prefers a compatible resource-designated detached container, then an unassigned container with free capacity.")
    add_bullets(doc, [
        "Probe deuterium is displayed as a percentage of capacity.",
        "Bulk metals, ice, carbon compounds, and other resources use ECE quantities.",
        "Inventory entries identify their containing probe or container whenever the API provides that relationship.",
        "Container policies may reserve a container for one resource type or leave it open to any resource.",
        "Transfer and rename commands remain subject to API capability and safety review.",
    ])
    add_note(doc, "Coverage limitation", "Detached-container contents and planet-dropped container details may be hidden by current observation endpoints. Skunkworks labels unavailable data instead of inventing quantities.")
    add_workspace_diagram(doc, "resources", "Resources & Inventory", [
        ("Resource overview", "Probe storage, drifting/placed containers, and asteroid reserves."),
        ("Inventory containers", "Container contents, capacity, assignment, and reservations."),
        ("Transfer controls", "Move stock, containers, Mannys, or deuterium between valid owners."),
        ("Deployment & recovery", "Jettison, place, salvage, or recover containers manually."),
    ])

    doc.add_page_break()
    add_heading(doc, "Missions workspace", 2)
    add_body(doc, "Missions lists live game objectives and progress. Open an entry for its available API detail; Skunkworks does not invent hidden quest steps.")
    add_workspace_diagram(doc, "missions", "Missions workspace", [
        ("Mission list", "All active or known objectives for the focused account context."),
        ("Mission state", "Status, progress, and timestamps supplied by the game."),
        ("Detail panel", "Selected mission description and currently exposed requirements."),
        ("Refresh context", "Reload after completing game actions in another window."),
    ])

    doc.add_page_break()
    add_heading(doc, "Production workspace", 2)
    add_body(doc, "Production shows every Manny and printer, including idle workers, with progress, local completion time, countdown, target, and the concise automation reason for work started by Skunkworks. Manual Build Order starts a selected recipe without making it a persistent desired-state target, while still respecting higher-priority allocations.")
    add_workspace_diagram(doc, "production", "Production workspace", [
        ("Manual build order", "Choose a recipe and eligible idle Manny, then queue one build."),
        ("Worker cards", "Crafting, mining, repair, upgrade, assembly, and idle status."),
        ("Timing", "Local 24-hour completion time plus a live HH:MM:SS countdown."),
        ("Automation reason", "The immediate order amount and one primary goal it supports."),
    ])

    doc.add_page_break()
    add_heading(doc, "7. Settings and Automation")
    add_body(doc, "Settings begins with account access, followed by audio, automation authority, desired-state targets, probe roles, safety floors, and help links. Automation policies, targets, priorities, reserves, and safety floors are stored separately for each focused probe. Owned probe roles are fleet-wide and can only be changed while the main/default probe is focused. Read the section labels before changing values; quantity and priority controls answer different questions.")
    add_body(doc, "Check for Updates opens the official latest-release channel. Download the signed package for the current operating system; the running application never silently replaces itself or bypasses platform security checks. Open Diagnostic Logs opens the per-user support folder containing rotating error logs that can be attached to a bug report. API keys, authorization tokens, and secrets are redacted automatically.")
    add_body(doc, "API compatibility is checked at startup and every six hours. If the server advertises an unreviewed API version, Skunkworks keeps the last valid snapshot visible, labels it stale, and pauses live commands until compatibility has been reviewed. This version check does not consume the probe request budget.")
    if has_settings_figure:
        doc.add_picture(str(SETTINGS_FIGURE), width=Inches(6.7))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font(caption.add_run("Figure 7-1. Settings workspace: command authority and desired-state controls."), size=9, color=MUTED)
        add_settings_legend(doc)
    add_note(doc, "More settings below", "Scroll to configure probe roles, live target status, resource and safety floors, and the Help & Documentation links.")

    add_heading(doc, "Automation and priorities", 2)
    add_body(doc, "Automation configuration is probe-specific. The mode, live-order permission, command allowlist, maximum orders per cycle, targets, priorities, reserves, and safety floors shown in Settings belong to the focused probe. Switching probes loads that probe's saved configuration and queue; a command prepared for one probe cannot be dispatched under another probe's policy. Probe-role assignments are the fleet-wide exception and are editable only from the main/default probe.")
    add_body(doc, "Automation targets describe a desired state. Priority uses a 1–10 scale: 1 is highest; equal numbers receive equal priority. Numeric selectors can be changed with their minus and plus buttons or by clicking the displayed number, typing a replacement, and pressing Enter. Bounds still apply. The planner compares targets with existing inventory, active work, available Mannys, recipes, resource needs, fuel floors, and safety policy.")
    add_note(doc, "Reading command rows", "Each command row now names its actual output after the command type—for example, MANNY CRAFT · ADDITIONAL CONTAINER or MANNY CRAFT · SCUT RELAY. The P-number is the current saved priority of that specific output target. Several Manny Craft rows with different priorities are distinct targets, not historical copies of one target.")
    add_note(doc, "Allocation ledger", "Active crafting outputs count toward the goal that requested them, preventing duplicate work. During each planning cycle, higher-priority operations claim their required stored resources and component items first. Lower-priority commands cannot spend those claims; equal-priority goals are evaluated in stable target order and refreshed against live inventory before execution.")
    add_heading(doc, "Recommended commissioning sequence", 2)
    add_steps(doc, [
        "Set target quantities for probes, tankers, Mannys, containers, SCUT relays, and transit beacons.",
        "Assign priorities from 1 to 10. Use equal values when outcomes are equally important.",
        "Set resource reserves and minimum fuel/free-capacity floors.",
        "Choose Observe Only and run one evaluation cycle.",
        "Inspect the proposed command queue and its explanation of why each command exists or why no action is available.",
        "Enable only the command types you are willing to send, then choose Approval or Automatic.",
    ])
    add_note(doc, "Mining quantities", "Maximum per Manny Mining Order is stored separately for each probe and accepts 0.05–0.55 ECE in 0.05 increments. A Manny carries 0.05 ECE per trip, so a larger order remains one continuous multi-trip campaign. Lower the maximum to return Mannys to the available pool sooner and let Skunkworks reconsider other work more frequently; 0.55 ECE preserves the longest, least-interrupted campaign behavior. The planner still tracks the full uncovered requirement and sends another capped order later when it remains necessary.")
    add_heading(doc, "Max orders per cycle", 2)
    add_body(doc, "This limit is the maximum number of separate live game orders Skunkworks may send during one 60-second automatic cycle. It is a rate and blast-radius control, not a target quantity.")

    add_heading(doc, "8. Safety Controls")
    add_bullets(doc, [
        "Travel-distance risk warns when a proposed journey may destroy a probe.",
        "Cargo-detachment risk increases when carrying five or more containers.",
        "Fuel-floor checks consider outbound travel, return travel, and whether either endpoint has a usable deuterium source.",
        "Resource depletion warns before a mining base exhausts its local source and reminds the operator that at most five wandering asteroids may spawn per system.",
        "Safety profiles warn and request acknowledgement; they do not permanently forbid a user-chosen risk unless an explicit stop policy is selected.",
        "Emergency Stop prevents all automation commands until cleared.",
    ])
    add_note(doc, "Observed rules", "Some hazards are observed game behavior rather than formally documented API guarantees. Skunkworks must identify the evidence level and keep thresholds configurable where uncertainty remains.", "warning")

    doc.add_page_break()
    add_heading(doc, "9. Audio, Logbook, and Daily Use")
    add_heading(doc, "Audio", 2)
    add_bullets(doc, [
        "Background Music enables the cinematic soundtrack and stores its volume separately.",
        "Interface Effects controls clicks, confirmations, warnings, loading, and discovery cues.",
        "Hover Sounds adds subtle feedback to supported navigation, selector, and map targets. It is disabled by default.",
        "Use Test Effect after changing audio output or volume.",
    ])
    add_heading(doc, "Logbook", 2)
    add_body(doc, "The logbook holds user-authored probe notes and, when enabled, significant Skunkworks work or discovery reports. Routine refreshes should not become log entries. Existing game pages should be listed and remain editable or deletable when the API permits those operations.")
    add_heading(doc, "Suggested session closeout", 2)
    add_steps(doc, [
        "Review Safety and clear or acknowledge outstanding findings.",
        "Confirm active missions and production work are consistent with current priorities.",
        "Review autonomous transport routes and protected deuterium floors.",
        "Create a logbook summary for discoveries, completed construction, stranded probes, and next-session objectives.",
        "Use Emergency Stop before closing if live automation should not continue.",
    ])
    add_note(doc, "Completion times", "Active work shows the estimated end as a local calendar date, 24-hour time, timezone abbreviation, and UTC offset. A live HH:MM:SS countdown appears beneath the estimate and updates once per second.")
    add_note(doc, "Mining targets", "Production details show the API's current public planet or asteroid name. Internal object identifiers are used only when the API does not provide a public label.")

    add_heading(doc, "10. Troubleshooting Quick Reference")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    set_table_geometry(table, [2200, 3100, 4060])
    for i, label in enumerate(("Symptom", "Check", "Action")):
        shade(table.rows[0].cells[i], "E8EEF5")
        font(table.rows[0].cells[i].paragraphs[0].add_run(label), bold=True, color=BLUE)
    cases = [
        ("Music works; effects are silent", "Interface Effects, effect volume, and Test Effect", "Restart after an audio-device change; verify the Qt FFmpeg backend decodes the selected effect."),
        ("Selected probe shows another probe’s sector", "Focused Probe name and FCC coordinates after refresh", "Refresh; do not act until the authoritative probe snapshot replaces the previous context."),
        ("No automation command is queued", "Targets, inventory, active work, idle assets, allowlist, and safety state", "Read the queue explanation; lower conflicting priorities or supply the missing prerequisite."),
        ("Status is Ready but readiness is below 100%", "Open Safety and inspect notice-level findings", "No action is required for health state; notices such as all Mannies being busy are advisory."),
        ("Qt cocoa platform plugin missing", "Active virtual environment and PySide6 installation", "Use the project `.venv`; avoid mixing Qt/PySide installations from different Python environments."),
        ("Map lacks sector detail", "Knowledge level and last scan", "Scan the sector or its neighbors; unavailable historic detail cannot be reconstructed automatically."),
    ]
    for case in cases:
        cells = table.add_row().cells
        for cell, text in zip(cells, case):
            font(cell.paragraphs[0].add_run(text), size=9.2)
        set_table_geometry(table, [2200, 3100, 4060])

    add_heading(doc, "Glossary", 1)
    for term, definition in (
        ("ECE", "The game’s resource/capacity quantity unit."),
        ("FCC", "Three-dimensional sector coordinates: X, Y, and Z."),
        ("Manny", "Autonomous construction and mining unit."),
        ("SCUT relay", "Communication relay that can participate in the discovered network."),
        ("SCUT transit beacon", "Equipment installed for SCUT transit functionality."),
        ("Desired state", "The quantities and priorities automation attempts to maintain."),
        ("Focused probe", "The probe whose operational context drives the current workspace."),
    ):
        add_body(doc, f"{term}. {definition}", bold_lead=f"{term}. ")

    doc.add_page_break()
    add_heading(doc, "Limited Interstellar Warranty")
    add_body(doc, "Congratulations. Your Skunkworks installation is covered by the finest warranty that can be printed without creating any enforceable obligations whatsoever.")
    add_bullets(doc, [
        "Coverage includes one sympathetic nod following an avoidable fuel-floor warning.",
        "Manny oil changes are recommended every 3,000 ECE mined. No oil port has been located, but preventive maintenance builds character.",
        "Cargo detached after carrying five or more containers is considered an unscheduled logistics exercise.",
        "Travel into a black hole may void the warranty, the probe, and several conventional definitions of 'return trip.'",
        "Emergency Stop is not a decorative button. Warranty adjusters become nervous when it is treated as one.",
    ])
    add_note(doc, "Actual terms", "Skunkworks is an independent community tool. The game server remains authoritative, and no joke on this page overrides the safety warnings, software license, or game rules.", "warning")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
