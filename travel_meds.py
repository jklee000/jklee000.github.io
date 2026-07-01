#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
여행 상비약 추천 · 복약 주의 가이드 (미니 프로젝트 프로토타입)

입력: 여행지 유형(택1) + 동반자 구성(복수)
출력: ① 성분별 상비약 체크리스트(표)
      ② 성분별 주의·금기 + 동반자별 주의 + 상담 권고
      ③ 고정 면책 문구

안전 원칙: 구체적 복용 '용량(숫자)'은 출력하지 않는다.
           성분명·대표 계열·주의/금기·상담 권고로 대체한다.

사용법:
  python travel_meds.py                         # 대화형 입력
  python travel_meds.py --demo                  # 데모(동남아 + 성인,아동)
  python travel_meds.py -d 동남아 -c 성인 아동   # 인자 직접 지정
"""

import argparse
import json
import os
import sys

# Windows 콘솔(cp949) 등에서 한글·기호가 깨지지 않도록 UTF-8 출력 강제
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DISCLAIMER = (
    "본 결과는 일반의약품에 대한 정보 제공용이며 의학적 진단·처방이 아닙니다.\n"
    "  실제 복용 용량과 가능 여부는 반드시 의사·약사와 상담하세요.\n"
    "  지속·악화되는 증상, 고열·혈변·호흡곤란 등은 즉시 현지 병원 진료를 받으세요."
)


# ---------- 데이터 로드 ----------
def load_json(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- 한글(전각) 폭을 고려한 표 정렬 ----------
def display_width(text):
    """전각 문자는 2칸으로 계산해 콘솔 정렬을 맞춘다."""
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 0x1100 and _is_wide(ch) else 1
    return width


def _is_wide(ch):
    code = ord(ch)
    return (
        0x1100 <= code <= 0x115F      # 한글 자모
        or 0x2E80 <= code <= 0xA4CF   # CJK 부수~한자
        or 0xAC00 <= code <= 0xD7A3   # 한글 완성형
        or 0xF900 <= code <= 0xFAFF   # CJK 호환 한자
        or 0xFF00 <= code <= 0xFF60   # 전각 기호
        or 0x3000 <= code <= 0x303F   # CJK 기호/구두점
    )


def pad(text, width):
    gap = width - display_width(text)
    return text + " " * max(gap, 0)


# ---------- 추천 로직 ----------
def recommend(meds, dest_tags):
    """모든 약을 기본 키트로 두되, 여행지 '특화' 태그와 겹치면 '강조' 표시.
    'general'(기본 상비) 태그는 변별력이 없으므로 강조 매칭에서 제외한다."""
    dest_set = set(dest_tags) - {"general"}
    result = []
    for med in meds:
        emphasized = bool((set(med["tags"]) - {"general"}) & dest_set)
        result.append({"med": med, "emphasized": emphasized})
    # 강조 약을 위로, 그 안에서는 원래 순서 유지
    result.sort(key=lambda x: not x["emphasized"])
    return result


# ---------- 출력 ----------
def print_header(dest_key, dest_info, companions):
    print("=" * 64)
    print(" 여행 상비약 추천 · 복약 주의 가이드")
    print("=" * 64)
    print(f" 여행지   : {dest_info['label']}")
    print(f" 동반자   : {', '.join(companions)}")
    print(f" 메모     : {dest_info.get('note', '')}")
    print()


def print_checklist(recommendations):
    print("[1] 성분별 상비약 체크리스트  (★ = 이 여행지에서 특히 중요)")
    print("-" * 64)
    cols = [("✔", 3), ("분류", 20), ("성분명", 34), ("용도", 28)]
    header = "".join(pad(name, w) for name, w in cols)
    print(header)
    print("-" * display_width(header))
    for item in recommendations:
        med = item["med"]
        mark = "★" if item["emphasized"] else "□"
        row = [
            (mark, 3),
            (med["category"], 20),
            (med["ingredient"], 34),
            (med["purpose"], 28),
        ]
        print("".join(pad(str(v), w) for v, w in row))
    print()


def print_cautions(recommendations, companions):
    print("[2] 성분별 주의 · 금기 사항")
    print("-" * 64)
    for item in recommendations:
        med = item["med"]
        star = "★ " if item["emphasized"] else "  "
        print(f"{star}● {med['ingredient']}  ({med['drug_class']})")
        for c in med["cautions"]:
            print(f"     - {c}")
        # 선택한 동반자에게 해당하는 경고만 노출
        cw = med.get("companion_warnings", {})
        for comp in companions:
            if comp in cw:
                print(f"     ⚠ [{comp}] {cw[comp]}")
        print(f"     (출처: {med['source']})")
        print()


def print_disclaimer():
    print("[3] 안내 (반드시 확인)")
    print("-" * 64)
    print("  " + DISCLAIMER)
    print("=" * 64)


# ---------- 입력 처리 ----------
def parse_companions(raw_list, valid):
    """입력 동반자 중 유효한 항목만 추리고, 없으면 '성인' 기본."""
    chosen = [c for c in raw_list if c in valid]
    return chosen or ["성인"]


def interactive_input(destinations, valid_companions):
    print("여행지 유형을 선택하세요:")
    keys = list(destinations.keys())
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k} - {destinations[k]['label']}")
    while True:
        sel = input("번호 입력: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(keys):
            dest_key = keys[int(sel) - 1]
            break
        print("  올바른 번호를 입력하세요.")

    print(f"\n동반자 구성을 선택하세요 (복수 가능, 공백/콤마 구분) {valid_companions}:")
    raw = input("입력: ").replace(",", " ").split()
    companions = parse_companions(raw, valid_companions)
    return dest_key, companions


def main():
    meds = load_json("meds.json")
    destinations = load_json("destinations.json")
    valid_companions = ["성인", "아동", "고령자", "임산부"]

    parser = argparse.ArgumentParser(description="여행 상비약 추천 가이드")
    parser.add_argument("-d", "--destination", choices=list(destinations.keys()),
                        help="여행지 유형")
    parser.add_argument("-c", "--companions", nargs="+", default=None,
                        help="동반자 구성 (성인 아동 고령자 임산부)")
    parser.add_argument("--demo", action="store_true", help="데모 실행")
    args = parser.parse_args()

    if args.demo:
        dest_key, companions = "동남아", ["성인", "아동"]
    elif args.destination:
        dest_key = args.destination
        companions = parse_companions(args.companions or [], valid_companions)
    else:
        dest_key, companions = interactive_input(destinations, valid_companions)

    dest_info = destinations[dest_key]
    recommendations = recommend(meds, dest_info["tags"])

    print()
    print_header(dest_key, dest_info, companions)
    print_checklist(recommendations)
    print_cautions(recommendations, companions)
    print_disclaimer()


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"데이터 파일을 찾을 수 없습니다: {e.filename}", file=sys.stderr)
        sys.exit(1)
