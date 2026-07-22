"""
interpret.py
---------------------------------
ตรรกะตัดสิน S / I / R — port ตรงจาก frontend src/lib/interpret.js (web_spec §5.2/5.3)
กติกา:  d >= s_min -> S | d <= r_max -> R | ระหว่างนั้น -> I

โหลด breakpoints จาก src/mocks/breakpoints.json ของ frontend (source of truth เดียวกัน)
*** breakpoints ยัง verified_by_lab=false — ยังห้ามใช้ตัดสินผลจริงจนทีมแลปรับรอง ***
"""
import json
import re
from pathlib import Path

# breakpoints (ฉบับแลปรับรอง) อยู่ข้างไฟล์นี้ใน backend — สร้างด้วย gen_breakpoints.py
# (deploy-friendly: ไม่พึ่ง path frontend) override ได้ด้วย env ZONESCOPE_BREAKPOINTS
BACKEND_BP = Path(__file__).with_name("breakpoints.json")


def _bp_path(path=None):
    import os
    return Path(path or os.environ.get("ZONESCOPE_BREAKPOINTS") or BACKEND_BP)


def load_breakpoints(path=None):
    return json.loads(_bp_path(path).read_text(encoding="utf-8"))


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def disk_alias_map(bp):
    """{normalized disk-code -> system code} สำหรับแปลงผล OCR เป็นรหัสในเกณฑ์"""
    m = {}
    for a in bp.get("antibiotics", []):
        code = a["code"]
        for alias in a.get("disk_aliases", []) + [code]:
            m[_norm(alias)] = code
    return m


def ocr_candidates(bp):
    """รายชื่อรหัสที่พิมพ์บนแผ่น (disk aliases) ไว้ให้ OCR จับคู่ (ก่อน map เป็น system code)"""
    out = set()
    for a in bp.get("antibiotics", []):
        for alias in a.get("disk_aliases", []) + [a["code"]]:
            if alias.strip():
                out.add(alias.strip())
    return sorted(out)


def interpret(bp, organism, antibiotic, diameter_mm):
    """คืน dict {result: 'S'|'I'|'R'|'N/A', rule, reason?}"""
    if not bp or not organism or not antibiotic or diameter_mm is None:
        return {"result": "N/A", "rule": None, "reason": "ยังระบุไม่ครบ"}
    rule = next(
        (r for r in bp["rules"]
         if r["organism"] == organism and r["antibiotic"] == antibiotic),
        None,
    )
    if not rule:
        return {"result": "N/A", "rule": None, "reason": "ไม่มีเกณฑ์สำหรับคู่เชื้อ+ยานี้"}
    if diameter_mm >= rule["s_min"]:
        return {"result": "S", "rule": rule}
    if diameter_mm <= rule["r_max"]:
        return {"result": "R", "rule": rule}
    return {"result": "I", "rule": rule}


def antibiotic_codes(bp):
    """รหัสยาทั้งหมดที่มีเกณฑ์ (closed set)"""
    return sorted({r["antibiotic"] for r in bp["rules"]})


def organisms(bp):
    return [(o["id"], o["label"]) for o in bp.get("organisms", [])]


if __name__ == "__main__":
    bp = load_breakpoints()
    print(f"standard: {bp.get('standard')}")
    print(f"verified_by_lab: {bp.get('verified_by_lab')}")
    print(f"organisms: {len(bp.get('organisms', []))} | rules: {len(bp['rules'])} | "
          f"antibiotics: {len(antibiotic_codes(bp))}")
    # ตัวอย่าง: E. coli + CIP5 ที่ค่าต่างๆ
    for d in (30, 22, 20):
        r = interpret(bp, "enterobacterales", "CIP5", d)
        print(f"  enterobacterales/CIP5 @ {d}mm -> {r['result']}")
