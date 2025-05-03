from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
import json
import difflib
import os
import subprocess

app = FastAPI()

# 카드 데이터 파일 경로
CARDS_FILE = "cards.json"

# 카드 데이터 로드 함수
def load_cards():
    if not os.path.exists(CARDS_FILE):
        return {}
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 카드 데이터 저장 함수
def save_cards(cards):
    with open(CARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

# 요청 모델
class CardRequest(BaseModel):
    query: str

class CardRegisterRequest(BaseModel):
    name: str
    data: dict  # 등록할 카드 정보 전체

class CardUpdateRequest(BaseModel):
    name: str
    update: dict  # 수정할 카드 필드들

class CardDeleteRequest(BaseModel):
    name: str

# 카드 정보 포맷 함수
def format_card_info(name, card):
    url = f"https://snap.fan/cards/{card['slug']}/"
    return {
        "name": name,
        "slug": card["slug"],
        "effect_ko": card["effect_ko"],
        "cost": card["cost"],
        "power": card["power"],
        "series": card["series"],
        "url": url
    }

# 카드 검색 API
@app.post("/card")
async def search_card(req: CardRequest):
    query = req.query.replace(" ", "").lower()
    card_data = load_cards()

    # 1. 정확 일치
    if query in card_data:
        card = card_data[query]
        return format_card_info(query, card)

    # 2. 포함 검색
    included = [key for key in card_data.keys() if query in key]
    if len(included) == 1:
        card = card_data[included[0]]
        return format_card_info(included[0], card)
    elif len(included) > 1:
        return {
            "message": f"중복된 카드명이 있습니다: {', '.join(included)}"
        }

    # 3. 유사도 검색
    possible_matches = difflib.get_close_matches(query, card_data.keys(), n=5, cutoff=0.6)
    if possible_matches:
        return {
            "message": f"중복된 카드명이 있습니다: {', '.join(possible_matches)}"
        }

    return {
        "message": "검색 결과가 없습니다."
    }

@app.get("/card")
def get_all_cards():
    return load_cards()

@app.get("/")
def read_root():
    return {"message": "Snapbot 서버 작동 중"}

# 카드 등록 API
@app.post("/add_card")
async def add_card(req: CardRegisterRequest):
    card_data = load_cards()

    name = req.name.replace(" ", "").lower()

    if name in card_data:
        raise HTTPException(status_code=400, detail="이미 존재하는 카드명입니다. 등록 불가합니다.")

    allowed_fields = ["effect_ko", "cost", "power", "series", "slug"]
    new_card = {}

    for key in allowed_fields:
        if key not in req.data:
            raise HTTPException(status_code=400, detail=f"필수 항목이 누락되었습니다: {key}")
        new_card[key] = req.data[key]

    card_data[name] = new_card
    save_cards(card_data)

    return {"result": "success", "message": f"{req.name} 카드 등록 완료"}

# 카드 수정 API
@app.post("/edit_card")
async def edit_card(req: CardUpdateRequest):
    card_data = load_cards()

    name = req.name.replace(" ", "").lower()

    if name not in card_data:
        raise HTTPException(status_code=404, detail="해당 카드명을 찾을 수 없습니다.")

    update_fields = req.update
    allowed_fields = ["effect_ko", "cost", "power", "series", "slug"]

    for key in allowed_fields:
        if key in update_fields:
            card_data[name][key] = update_fields[key]

    save_cards(card_data)

    return {"result": "success", "message": f"{req.name} 카드 수정 완료"}

# 카드 삭제 API
@app.post("/delete_card")
async def delete_card(req: CardDeleteRequest):
    card_data = load_cards()

    name = req.name.strip()

    if name not in card_data:
        raise HTTPException(status_code=404, detail="해당 카드명을 찾을 수 없습니다.")

    del card_data[name]
    save_cards(card_data)

    return {"result": "success", "message": f"{req.name} 카드 삭제 완료"}

@app.get("/download_json")
def download_json():
    json_path = os.path.join(os.getcwd(), "cards.json")
    if os.path.exists(json_path):
        return FileResponse(path=json_path, filename="cards.json", media_type="application/json")
    else:
        return {"message": "cards.json 파일이 존재하지 않습니다."}