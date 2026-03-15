from io import BytesIO
from datetime import datetime


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 40
MARGIN_TOP = 54
MARGIN_BOTTOM = 44
LINE_HEIGHT = 13
TITLE_SIZE = 16
BODY_SIZE = 10
MAX_CHARS = 108


def _escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _chunk_text(line: str, size: int = MAX_CHARS) -> list[str]:
    if len(line) <= size:
        return [line]
    chunks = []
    start = 0
    while start < len(line):
        chunks.append(line[start:start + size])
        start += size
    return chunks


def _paginate(lines: list[str], lines_per_page: int) -> list[list[str]]:
    pages = []
    for i in range(0, len(lines), lines_per_page):
        pages.append(lines[i:i + lines_per_page])
    return pages or [["No data"]]


def build_text_pdf(title: str, lines: list[str]) -> bytes:
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    prepared = [
        f"Generated: {generated}",
        ""
    ]
    for line in lines:
        for chunk in _chunk_text(str(line)):
            prepared.append(chunk)

    usable_height = PAGE_HEIGHT - (MARGIN_TOP + MARGIN_BOTTOM + 30)
    lines_per_page = max(1, int(usable_height // LINE_HEIGHT))
    pages = _paginate(prepared, lines_per_page)

    objects: list[bytes] = []
    page_obj_ids = []
    content_obj_ids = []
    first_dynamic_id = 3
    font_obj_id = first_dynamic_id + (len(pages) * 2)

    for i, page_lines in enumerate(pages):
        page_obj_id = first_dynamic_id + (i * 2)
        content_obj_id = page_obj_id + 1
        page_obj_ids.append(page_obj_id)
        content_obj_ids.append(content_obj_id)

        text_stream = BytesIO()
        text_stream.write(b"BT\n")
        start_y = PAGE_HEIGHT - MARGIN_TOP
        text_stream.write(f"/F1 {TITLE_SIZE} Tf\n".encode())
        text_stream.write(f"{MARGIN_X} {start_y} Td\n".encode())
        text_stream.write(f"({_escape_pdf_text(title)}) Tj\n".encode())
        text_stream.write(f"0 {-20} Td\n".encode())
        text_stream.write(f"/F1 {BODY_SIZE} Tf\n".encode())
        text_stream.write(f"{LINE_HEIGHT} TL\n".encode())
        text_stream.write(f"({f'Page {i+1} of {len(pages)}'}) Tj\n".encode())
        text_stream.write(f"0 {-18} Td\n".encode())
        text_stream.write(f"({'-' * 92}) Tj\n".encode())
        text_stream.write(f"0 {-16} Td\n".encode())
        for line in page_lines:
            safe = _escape_pdf_text(line)
            text_stream.write(f"({safe}) Tj\nT*\n".encode())
        text_stream.write(b"ET\n")
        stream_bytes = text_stream.getvalue()

        content_obj = (
            f"{content_obj_id} 0 obj\n"
            f"<< /Length {len(stream_bytes)} >>\n"
            f"stream\n"
        ).encode() + stream_bytes + b"endstream\nendobj\n"
        objects.append(content_obj)

        page_obj = (
            f"{page_obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {content_obj_id} 0 R "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> >>\n"
            f"endobj\n"
        ).encode()
        objects.append(page_obj)

    objects_sorted = sorted(
        objects,
        key=lambda b: int(b.split(b" ", 1)[0])
    )

    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    pages_obj = (
        f"2 0 obj\n"
        f"<< /Type /Pages /Count {len(page_obj_ids)} /Kids [{kids}] >>\n"
        f"endobj\n"
    ).encode()

    catalog_obj = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    font_obj = (
        f"{font_obj_id} 0 obj\n"
        f"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\n"
        f"endobj\n"
    ).encode()

    all_objects = [catalog_obj, pages_obj] + objects_sorted + [font_obj]
    all_objects = sorted(all_objects, key=lambda b: int(b.split(b" ", 1)[0]))

    out = BytesIO()
    out.write(b"%PDF-1.4\n")

    offsets = [0]
    for obj in all_objects:
        offsets.append(out.tell())
        out.write(obj)

    xref_start = out.tell()
    out.write(f"xref\n0 {len(offsets)}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())

    out.write(
        (
            f"trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode()
    )
    return out.getvalue()
