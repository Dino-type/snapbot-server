import pandas as pd
import json

# 파일 경로
excel_path = "cards.xlsx"
json_path = "cards.json"

# 엑셀 로드 (헤더 없음)
df = pd.read_excel(excel_path, header=None)

# 카드 정보 딕셔너리 생성
cards = {}

for _, row in df.iterrows():
    name = str(row[0]).strip().replace(" ", "")  # A열: 카드명 (띄어쓰기 제거)
    cards[name] = {
        "effect_ko": str(row[1]).strip(),       # B열: 효과
        "cost": int(row[2]),                    # C열: 코스트
        "power": int(row[3]),                   # D열: 파워
        "series": int(row[4]),                  # E열: 시리즈
        "slug": str(row[5]).strip()             # F열: 슬러그
    }

# JSON 저장
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(cards, f, ensure_ascii=False, indent=2)

print(f"{len(cards)}장의 카드 정보를 '{json_path}' 파일로 저장했습니다.")
