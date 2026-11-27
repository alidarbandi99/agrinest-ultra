#!/usr/bin/env python3
"""Agrinest Eye: offline-first OCR and conservative water/soil lab extraction.

This tool does NOT diagnose a crop or prescribe fertilizers. Always review OCR.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ALIASES = {
    "ph": ["ph", "پی اچ", "اسیدیته"],
    "ec": ["ec", "e.c", "هدایت الکتریکی"],
    "ca": ["ca", "calcium", "کلسیم"],
    "mg": ["mg", "magnesium", "منیزیم"],
    "na": ["na", "sodium", "سدیم"],
    "k": ["k", "potassium", "پتاسیم"],
    "no3": ["no3", "nitrate", "نیترات"],
    "nh4": ["nh4", "ammonium", "آمونیوم"],
    "so4": ["so4", "sulfate", "sulphate", "سولفات"],
    "cl": ["cl", "chloride", "کلراید", "کلرید"],
    "hco3": ["hco3", "bicarbonate", "بی کربنات", "بی‌کربنات"],
    "co3": ["co3", "carbonate", "کربنات"],
    "b": ["boron", "بور"],
    "fe": ["fe", "iron", "آهن"],
    "mn": ["mn", "manganese", "منگنز"],
    "zn": ["zn", "zinc", "روی"],
    "cu": ["cu", "copper", "مس"],
    "p": ["phosphorus", "فسفر"],
    "sar": ["sar"],
    "rsc": ["rsc"],
    "organic_matter": ["organic matter", "ماده آلی"],
    "organic_carbon": ["organic carbon", "کربن آلی"],
}
# Avoid accidental chemical symbol matches inside words.
SHORT_SYMBOLS = {key for key in ALIASES if len(key) <= 3}
NUM = r"[-+]?\d+(?:[.,]\d+)?"
UNITS = r"(?:mg\s*/\s*l|ppm|meq\s*/\s*l|mmol\s*/\s*l|dS\s*/\s*m|mS\s*/\s*cm|µS\s*/\s*cm|uS\s*/\s*cm|%|mg\s*/\s*kg)"
VALUE_RE = re.compile(r"(?<![\w])(" + NUM + r")(?![\w])")
UNIT_RE = re.compile(UNITS, re.I)
RANGE = {"ph": (0.0, 14.0), "ec": (0.0, 100.0), "sar": (0.0, 1000.0)}

def normalize(text: str) -> str:
    return (text.replace("٫", ".").replace("،", ".").replace("−", "-")
            .translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            .replace("\u200c", " ").replace("\u200f", " "))

def key_in_line(line: str) -> tuple[str, int, int] | None:
    """Identify a labelled row; return earliest identifier. No inferred values."""
    low = normalize(line).lower()
    candidates = []
    for key, forms in ALIASES.items():
        for form in forms:
            match = re.search(r"(?<![a-z0-9])" + re.escape(form.lower().replace("\u200c", " ")) + r"(?![a-z0-9])", low)
            if match:
                candidates.append((match.start(), -(match.end()-match.start()), key, match.end()))
    if not candidates:
        return None
    candidates.sort()
    pos, _, key, end = candidates[0]
    return key, pos, end

def parse_text(text: str, kind: str = "auto") -> dict[str, Any]:
    """Extract labelled values only; preserve raw text, ambiguity and units."""
    if kind not in ("auto", "water", "soil"):
        raise ValueError("kind must be auto, water or soil")
    measurements: dict[str, list[dict[str, Any]]] = {}
    review: list[str] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = normalize(raw).strip()
        if not line:
            continue
        found = key_in_line(line)
        if not found:
            continue
        key, pos, end = found
        # Restrict extraction to data appearing after the row label.
        tail = line[end:].strip(" :：=\t|-")
        value_match = VALUE_RE.search(tail)
        if not value_match:
            review.append(f"Line {number}: {key} identified but no numeric value")
            continue
        token = value_match.group(1)
        if "," in token and "." not in token:
            # A comma could be a decimal separator or grouping separator.
            review.append(f"Line {number}: ambiguous comma in {key}: {token}")
            continue
        value = float(token)
        unit_match = UNIT_RE.search(tail[value_match.end():])
        unit = unit_match.group(0).replace(" ", "") if unit_match else None
        if unit is None and key not in ("ph", "sar", "rsc"):
            review.append(f"Line {number}: unit missing for {key}")
        if key in RANGE and not (RANGE[key][0] <= value <= RANGE[key][1]):
            review.append(f"Line {number}: {key} outside basic plausibility bounds")
        measurements.setdefault(key, []).append({
            "value": value, "unit_original": unit,
            "line": number, "raw_line": raw,
            "status": "needs_review" if unit is None and key not in ("ph", "sar", "rsc") else "extracted"
        })
    for key, entries in measurements.items():
        if len(entries) > 1:
            review.append(f"Multiple candidates for {key}; review before using")
    return {
        "document_type": kind,
        "measurements": measurements,
        "review_required": bool(review),
        "review_notes": review,
        "warnings": [
            "OCR output is not verified laboratory data.",
            "Do not use for nutrient prescriptions until values, chemical basis and units are checked.",
            "NO3 and NO3-N, SO4 and S, and EC units must not be treated as interchangeable."
        ],
        "raw_text": text,
    }

def ocr_file(path: Path, lang: str = "fas+eng") -> tuple[str, list[str]]:
    """Read images/PDF locally; dependencies and tessdata must be installed."""
    import pytesseract
    from PIL import Image, ImageOps, ImageEnhance
    warnings: list[str] = []
    pages = []
    if path.suffix.lower() == ".pdf":
        import fitz
        with fitz.open(str(path)) as pdf:
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDF not supported")
            if len(pdf) > 30:
                raise ValueError("PDF exceeds 30-page processing limit")
            for i, page in enumerate(pdf):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pages.append((i + 1, image))
    else:
        with Image.open(path) as im:
            if im.width * im.height > 40_000_000:
                raise ValueError("Image exceeds pixel limit")
            pages.append((1, im.convert("RGB")))
    blocks = []
    for i, image in pages:
        gray = ImageOps.grayscale(image)
        gray = ImageEnhance.Contrast(gray).enhance(1.5)
        try:
            output = pytesseract.image_to_string(gray, lang=lang, config="--psm 6")
        except pytesseract.TesseractError as exc:
            raise RuntimeError("OCR engine or fas/eng language models unavailable") from exc
        if not output.strip():
            warnings.append(f"Page {i}: OCR produced no text")
        blocks.append(f"\n--- PAGE {i} ---\n" + output)
    return "\n".join(blocks), warnings

def main() -> None:
    parser = argparse.ArgumentParser(description="Agrinest Eye: inspect water/soil lab report")
    parser.add_argument("file", type=Path, help="PDF/image, or UTF-8 .txt for dry run")
    parser.add_argument("--type", choices=["auto", "water", "soil"], default="auto")
    parser.add_argument("--lang", default="fas+eng")
    parser.add_argument("--output", type=Path, help="Optional local JSON output path")
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error("Input file does not exist")
    if args.file.suffix.lower() == ".txt":
        text = args.file.read_text(encoding="utf-8")
        warnings = []
    elif args.file.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"):
        text, warnings = ocr_file(args.file, args.lang)
    else:
        parser.error("Unsupported input type")
    result = parse_text(text, args.type)
    result["warnings"].extend(warnings)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)

if __name__ == "__main__":
    main()
