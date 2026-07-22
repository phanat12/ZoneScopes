"""
gen_breakpoints.py
---------------------------------
สร้าง breakpoints.json จาก AST_data_review2.xlsx (**ฉบับแลปรับรองแล้ว**)

- sheet "Breakpoints" -> rules[{organism, antibiotic(system code), s_min, r_max, i_range}]
- sheet "รหัสยา"      -> antibiotics[{code, name, amount, disk_aliases}] (เชื่อม OCR disk code -> system code)
- organisms[] slug จากชื่อกลุ่มเชื้อ (แตกหลายเชื้อต่อแถวด้วย comma)
- verified_by_lab = true

เขียนออก 2 ที่: backend (source of truth ให้ /api/breakpoints) + frontend mock

รัน:  python gen_breakpoints.py
"""
import json
import re
from pathlib import Path

import openpyxl

BACKEND = Path(__file__).resolve().parent
XLSX = Path(r"C:\Users\Administrator\Downloads\22\ZoneScope-main\AST_data_review2.xlsx")
OUT_BACKEND = BACKEND / "breakpoints.json"
OUT_FRONTEND = Path(
    r"C:\Users\Administrator\Downloads\22\ZoneScope-main\ZoneScope-main\ZoneScope-main"
    r"\src\mocks\breakpoints.json"
)
STANDARD = ("SD-IN-03-MI-BM-002 Zone Diameter Interpretive Standards 2026 "
            "(CLSI M100 2026 / M45 3rd / EUCAST 2026) — ผ่านการตรวจรับรองจากทีมแลปแล้ว")


def slug(name):
    s = (name or "").strip().lower().replace("β", "beta")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def num(v):
    if v is None:
        return None
    m = re.search(r"\d+", str(v))
    return int(m.group()) if m else None


def main():
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

    # ---- antibiotics (รหัสยา) ----
    antibiotics, alias2code = [], {}
    for r in wb["รหัสยา"].iter_rows(min_row=2, values_only=True):
        if not r or r[0] is None:
            continue
        code = str(r[0]).strip()
        name = str(r[1] or "").strip()
        amount = str(r[2] or "").strip()
        aliases = [a.strip() for a in str(r[3] or "").split(",") if a.strip()]
        # frontend (AntibioticSelect/Results) ใช้ code + label
        antibiotics.append({"code": code, "label": f"{name} ({amount})" if amount else name,
                            "name": name, "amount": amount, "disk_aliases": aliases})
        for a in aliases + [code]:
            alias2code[re.sub(r"[^A-Z0-9]", "", a.upper())] = code

    # ---- rules (Breakpoints) ----
    rules, organisms, org_seen, dupes = [], [], {}, []
    seen_pairs = set()
    for r in wb["Breakpoints"].iter_rows(min_row=2, values_only=True):
        if not r or r[1] is None:
            continue
        code = str(r[1]).strip()
        s_min, r_num = num(r[5]), num(r[7])
        i_raw = str(r[6]).strip() if r[6] not in (None, "-") else "-"
        if s_min is None:
            continue
        r_max = r_num if r_num is not None else s_min - 1     # S-only -> S/R เท่านั้น
        for org_name in str(r[3] or "").split(","):
            org_name = org_name.strip()
            if not org_name:
                continue
            oid = slug(org_name)
            if oid not in org_seen:
                org_seen[oid] = org_name
                organisms.append({"id": oid, "label": org_name})
            key = (oid, code)
            if key in seen_pairs:                # กันเกณฑ์ซ้ำ (คู่เชื้อ+ยา) -> เก็บอันแรก
                dupes.append(key)
                continue
            seen_pairs.add(key)
            rules.append({"organism": oid, "antibiotic": code,
                          "s_min": s_min, "r_max": r_max, "i_range": i_raw})

    organisms.sort(key=lambda o: o["label"])
    data = {
        "standard": STANDARD,
        "verified_by_lab": True,
        "organisms": organisms,
        "antibiotics": antibiotics,
        "rules": rules,
    }

    for out in (OUT_BACKEND, OUT_FRONTEND):
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"organisms : {len(organisms)}")
    print(f"antibiotics: {len(antibiotics)} (disk-code aliases -> system code: {len(alias2code)})")
    print(f"rules      : {len(rules)}  (ข้ามคู่ซ้ำ {len(dupes)}: {dupes})")
    print(f"เขียน -> {OUT_BACKEND}")
    print(f"เขียน -> {OUT_FRONTEND}")


if __name__ == "__main__":
    main()
