from __future__ import annotations

from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
from copy import deepcopy

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .models import NarrativeResponse


def export_narrative_to_pdf(narrative: NarrativeResponse, output_path: str | Path) -> Path:
    """
    Minimal ReportLab export stub.

    The function already produces a simple PDF so the project has a working
    export path, but the layout is intentionally basic and meant to be replaced
    with a richer Form T661 template later.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"ShRED - {narrative.project_name}")

    pdf.setFont("Helvetica", 10)
    y -= 30
    for label, value in [
        ("Evidence Summary", narrative.evidence_summary),
        ("Scientific Uncertainty", narrative.scientific_uncertainty),
        ("Technical Advancement", narrative.technical_advancement),
    ]:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, label)
        y -= 16
        pdf.setFont("Helvetica", 10)
        for line in value.splitlines():
            pdf.drawString(60, y, line[:110])
            y -= 14
            if y < 60:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)
        y -= 8

    pdf.save()
    return path


def _words(text: str, limit: int) -> str:
    return " ".join(text.split()[:limit])


def _draw_wrapped(pdf: canvas.Canvas, text: str, x: float, y: float, width: float, line_height: float, max_lines: int) -> None:
    words = text.split()
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, "Helvetica", 7) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    for item in lines[:max_lines]:
        pdf.drawString(x, y, item)
        y -= line_height


def export_narrative_to_t661(
    narratives: list[NarrativeResponse],
    output_path: str | Path,
    claimant_name: str = "JJ Jameson",
    tax_year_start: str = "2026-01-01",
    tax_year_end: str = "2026-12-31",
    project_title: str = "",
    project_code: str = "",
) -> Path:
    """Overlay the generated project information onto CRA's static T661 template."""
    narratives = [narrative for narrative in narratives if narrative.applicable]
    if not narratives:
        raise ValueError("At least one Applicable project is required to generate a T661")
    template = Path(__file__).resolve().parents[2] / "t661-fill-26e.pdf"
    if not template.exists():
        raise FileNotFoundError(f"CRA T661 template not found at {template}")

    source = PdfReader(str(template))
    acroform = source.trailer["/Root"].get("/AcroForm")
    if acroform and acroform.get_object().get("/XFA"):
        return _export_xfa_t661(
            source,
            template,
            output_path,
            narratives,
            claimant_name,
            tax_year_start,
            tax_year_end,
            project_title,
            project_code,
        )

    overlay = BytesIO()
    pdf = canvas.Canvas(overlay, pagesize=letter)
    width, height = letter

    # Page 1, Part 1: coordinates align with the blank T661 E (26) template.
    pdf.setFont("Helvetica", 8)
    pdf.drawString(75, 614, claimant_name[:90])
    pdf.drawString(165, 590, tax_year_start[:20])
    pdf.drawString(375, 590, tax_year_end[:20])
    pdf.drawString(275, 553, "1")
    pdf.drawString(75, 530, narratives[0].source_repository or "")
    pdf.showPage()

    # Page 2, Part 2: keep CRA section labels and place concise text in their boxes.
    pdf.setFont("Helvetica", 8)
    pdf.drawString(75, 680, f"{project_title or narratives[0].project_name} {project_code}".strip()[:90])
    pdf.drawString(190, 520, "Generated from repository evidence")
    _draw_wrapped(pdf, _words(narratives[0].scientific_uncertainty, 350), 55, 425, 500, 9, 10)
    _draw_wrapped(pdf, _words(narratives[0].technical_advancement, 700), 55, 280, 500, 9, 14)
    _draw_wrapped(pdf, _words(narratives[0].evidence_summary, 350), 55, 95, 500, 9, 4)
    pdf.showPage()

    for _ in range(len(source.pages) - 2):
        pdf.showPage()
    pdf.save()
    overlay.seek(0)

    overlay_reader = PdfReader(overlay)
    writer = PdfWriter()
    for index, page in enumerate(source.pages):
        if index < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[index])
        writer.add_page(page)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _set_xfa_value(root: ET.Element, field_path: str, value: str) -> None:
    target_name = field_path.rsplit("/", 1)[-1]
    for element in root.iter():
        if _local_name(element.tag) != target_name:
            continue
        element.text = value
        return
    raise ValueError(f"XFA field not found: {field_path}")


def _enable_repeating_project_pages(template_root: ET.Element) -> None:
    namespace = "http://www.xfa.org/schema/xfa-template/3.3/"
    for element in template_root.iter():
        if element.tag.rsplit("}", 1)[-1] != "subform":
            continue
        if element.attrib.get("name") not in {"Page2", "Page3"}:
            continue
        occur = next(
            (child for child in element if child.tag.rsplit("}", 1)[-1] == "occur"),
            None,
        )
        if occur is None:
            occur = ET.Element(f"{{{namespace}}}occur")
            element.insert(0, occur)
        occur.set("min", "0")
        occur.set("max", "-1")


def _export_xfa_t661(
    source: PdfReader,
    template: Path,
    output_path: str | Path,
    narratives: list[NarrativeResponse],
    claimant_name: str,
    tax_year_start: str,
    tax_year_end: str,
    project_title: str,
    project_code: str,
) -> Path:
    xfa = source.trailer["/Root"]["/AcroForm"].get_object()["/XFA"]
    datasets_stream = None
    template_stream = None
    for index in range(0, len(xfa), 2):
        if str(xfa[index]) == "datasets":
            datasets_stream = xfa[index + 1].get_object()
        elif str(xfa[index]) == "template":
            template_stream = xfa[index + 1].get_object()
    if datasets_stream is None:
        raise ValueError(f"XFA datasets packet not found in {template.name}")
    if template_stream is None:
        raise ValueError(f"XFA template packet not found in {template.name}")

    xfa_namespace = "http://www.xfa.org/schema/xfa-data/1.0/"

    root = ET.fromstring(datasets_stream.get_data())
    template_root = ET.fromstring(template_stream.get_data())
    _enable_repeating_project_pages(template_root)
    _set_xfa_value(root, "Name_010", claimant_name)
    _set_xfa_value(root, "FromDate", tax_year_start)
    _set_xfa_value(root, "ToDate", tax_year_end)
    _set_xfa_value(root, "Projects_050", str(len(narratives)))
    form = next((node for node in root.iter() if _local_name(node.tag) == "form1"), None)
    if form is None:
        raise ValueError("XFA form1 data group not found")
    pages = [node for node in list(form) if _local_name(node.tag) in {"Page2", "Page3"}]
    if len(pages) < 2:
        raise ValueError("XFA project page groups not found")
    page2, page3 = pages[0], pages[1]
    for node in pages:
        form.remove(node)
    for narrative in narratives:
        project_page = deepcopy(page2)
        project_page.set(f"{{{xfa_namespace}}}dataNode", "dataGroup")
        _set_xfa_value(project_page, "Field_200", f"{narrative.project_name} {project_code}".strip())
        _set_xfa_value(project_page, "Field_242", _words(narrative.scientific_uncertainty, 350))
        _set_xfa_value(project_page, "Field_244", _words(narrative.work_performed, 700))
        _set_xfa_value(project_page, "Field_246", _words(narrative.technical_advancement, 350))
        project_page3 = deepcopy(page3)
        project_page3.set(f"{{{xfa_namespace}}}dataNode", "dataGroup")
        form.append(project_page)
        form.append(project_page3)

    updated_datasets = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    updated_template = ET.tostring(template_root, encoding="utf-8", xml_declaration=False)
    datasets_stream.set_data(updated_datasets)
    template_stream.set_data(updated_template)

    writer = PdfWriter()
    writer.clone_document_from_reader(source)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)
    return path
