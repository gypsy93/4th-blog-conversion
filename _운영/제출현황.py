"""주차별 미션 제출 현황을 모아 제출현황.md 를 만든다.

    python _운영/제출현황.py              # 제출현황.md 갱신
    python _운영/제출현황.py --csv 1      # 1주차 제출 내용을 관리 시트 '미션' 탭에 붙일 CSV로 출력

명단은 _운영/명단.csv, 제출 파일은 N주차/제출/{닉네임}.md 에서 읽는다.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "제출현황.md"

# 주차별 제출 요건. 글 = 글1~글N 칸에 링크가 있어야 하는 수, 필수 = 비어 있으면 안 되는 칸.
# 요건이 없는 주차는 한 칸이라도 채우면 제출로 본다.
RULES = {
    1: {"글": 3, "필수": ["AI 없이 직접 쓴 글 (번호)"]},
    2: {"글": 3, "필수": ["트랙 (수익 / 검색 1위)", "제휴 링크 넣은 글 (번호)"]},
}

FIELD = re.compile(r"^\s*-\s*([^:\[\]]+?)\s*:\s*(.*?)\s*$")
CHECK = re.compile(r"^\s*-\s*\[([ xX])\]")
URL = re.compile(r"https?://\S+")


def load_members():
    with open(ROOT / "_운영" / "명단.csv", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r["닉네임"].strip()]


def weeks():
    found = []
    for d in ROOT.glob("*주차"):
        m = re.fullmatch(r"(\d+)주차", d.name)
        if m and (d / "제출").is_dir():
            found.append(int(m.group(1)))
    return sorted(found)


def parse(path):
    fields, checks = {}, [0, 0]
    for line in path.read_text(encoding="utf-8").splitlines():
        c = CHECK.match(line)
        if c:
            checks[1] += 1
            checks[0] += c.group(1) in "xX"
            continue
        m = FIELD.match(line)
        if m:
            fields[m.group(1)] = m.group(2)
    return fields, checks


def status(week, path):
    """(아이콘, 설명, 글 링크 목록)"""
    if not path.exists():
        return "⬜", "파일 없음", []
    fields, (done, total) = parse(path)
    rule = RULES.get(week, {"글": 0, "필수": []})
    posts = []
    for i in range(1, rule["글"] + 1):
        m = URL.search(fields.get(f"글{i}", ""))
        if m:
            posts.append(m.group(0))
    filled = any(v for v in fields.values()) or done > 0
    if not filled:
        return "⬜", "미제출", []
    missing = [k for k in rule["필수"] if not fields.get(k)]
    ok = len(posts) >= rule["글"] and not missing
    parts = []
    if rule["글"]:
        parts.append(f"글 {len(posts)}/{rule['글']}")
    if total:
        parts.append(f"체크 {done}/{total}")
    if missing:
        parts.append("빈 칸: " + ", ".join(k.split(" (")[0] for k in missing))
    return ("✅" if ok else "🟡"), " · ".join(parts) or "제출", posts


def build():
    members = load_members()
    crew = [m for m in members if m["역할"] != "운영"]
    ws = weeks()
    rows, summary = [], []
    results = {w: {} for w in ws}
    for w in ws:
        for m in crew:
            results[w][m["닉네임"]] = status(w, ROOT / f"{w}주차" / "제출" / f"{m['닉네임']}.md")
        icons = [r[0] for r in results[w].values()]
        summary.append(
            f"| [{w}주차]({w}주차/README.md) | {icons.count('✅')} | {icons.count('🟡')} | {icons.count('⬜')} | {len(crew)} |"
        )

    head = "| 닉네임 | 조 | " + " | ".join(f"{w}주차" for w in ws) + " |"
    sep = "|---|---|" + "---|" * len(ws)
    for m in crew:
        cells = []
        for w in ws:
            icon, note, _ = results[w][m["닉네임"]]
            link = f"{w}주차/제출/{m['닉네임']}.md"
            cells.append(f"{icon} [{note}]({link})" if icon != "⬜" else f"⬜ {note}")
        rows.append(f"| {m['닉네임']} | {m['조']} | " + " | ".join(cells) + " |")

    known = {m["닉네임"] for m in members}
    strays = sorted(
        f"{w}주차/제출/{p.name}"
        for w in ws
        for p in (ROOT / f"{w}주차" / "제출").glob("*.md")
        if not p.name.startswith("_") and p.stem not in known
    )

    lines = [
        "# 📊 제출 현황",
        "",
        "> 자동 생성 파일이에요. 직접 고치지 마세요 — 각자 `N주차/제출/내닉네임.md` 를 채우면 여기에 반영돼요.",
        ">",
        "> ✅ 제출 요건 충족 · 🟡 작성 중 (빠진 칸 있음) · ⬜ 미제출  ",
        "> 통과 여부와 쉘 지급은 유닛장이 확인 후 관리 시트에 기록해요.",
        "",
        "## 주차별 요약",
        "",
        "| 주차 | ✅ | 🟡 | ⬜ | 전체 |",
        "|---|---|---|---|---|",
        *summary,
        "",
        "## 크루별",
        "",
        head,
        sep,
        *rows,
    ]
    if strays:
        lines += ["", "## ⚠️ 명단에 없는 제출 파일", "", "파일 이름이 닉네임과 같은지 확인해 주세요.", ""]
        lines += [f"- [{s}]({s})" for s in strays]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUT.name} 갱신: " + ", ".join(f"{w}주차 ✅{s.count('✅')}" for w, s in
                                         ((w, [r[0] for r in results[w].values()]) for w in ws)))


def export_csv(week):
    """관리 시트 '미션' 탭 순서(명단 순)대로 글 링크를 출력한다."""
    n = RULES.get(week, {"글": 3})["글"] or 3
    w = csv.writer(sys.stdout)
    w.writerow(["닉네임"] + [f"{week}주 글{i}" for i in range(1, n + 1)] + ["상태"])
    for m in load_members():
        icon, _, posts = status(week, ROOT / f"{week}주차" / "제출" / f"{m['닉네임']}.md")
        w.writerow([m["닉네임"]] + (posts + [""] * n)[:n] + [icon])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "--csv":
        export_csv(int(sys.argv[2]))
    else:
        build()
