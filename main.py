# ✅ Snapbot FastAPI 서버 정리본
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import json
import difflib
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

app = FastAPI()

CARDS_FILE = "cards.json"

# 카드 데이터 로드 및 저장

def load_cards():
    if not os.path.exists(CARDS_FILE):
        return {}
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cards(cards):
    with open(CARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

# 요청 모델
class CardRequest(BaseModel):
    query: str

class CardRegisterRequest(BaseModel):
    name: str
    data: dict

class CardUpdateRequest(BaseModel):
    name: str
    update: dict

class CardDeleteRequest(BaseModel):
    name: str

# 카드 출력 포맷

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

@app.get("/")
def read_root():
    return {"message": "Snapbot 서버 작동 중"}

# 전체 카드 조회
@app.get("/card")
def get_all_cards():
    return load_cards()

# 카드 검색
@app.post("/card")
async def search_card(req: CardRequest):
    query = req.query.replace(" ", "").lower()
    card_data = load_cards()

    if query in card_data:
        return format_card_info(query, card_data[query])

    included = [key for key in card_data if query in key]
    if len(included) == 1:
        return format_card_info(included[0], card_data[included[0]])
    elif len(included) > 1:
        return {"message": f"중복된 카드명이 있습니다: {', '.join(included)}"}

    possible_matches = difflib.get_close_matches(query, card_data.keys(), n=5, cutoff=0.6)
    if possible_matches:
        return {"message": f"중복된 카드명이 있습니다: {', '.join(possible_matches)}"}

    return {"message": "검색 결과가 없습니다."}

# 카드 등록
@app.post("/add_card")
async def add_card(req: CardRegisterRequest):
    card_data = load_cards()
    name = req.name.replace(" ", "").lower()

    if name in card_data:
        raise HTTPException(status_code=400, detail="이미 존재하는 카드명입니다. 등록 불가합니다.")

    allowed_fields = ["effect_ko", "cost", "power", "series", "slug"]
    new_card = {key: req.data[key] for key in allowed_fields if key in req.data}

    if len(new_card) != len(allowed_fields):
        raise HTTPException(status_code=400, detail="필수 항목이 누락되었습니다.")

    card_data[name] = new_card
    save_cards(card_data)
    return {"result": "success", "message": f"{req.name} 카드 등록 완료"}

# 카드 수정
@app.post("/edit_card")
async def edit_card(req: CardUpdateRequest):
    card_data = load_cards()
    name = req.name.replace(" ", "").lower()

    if name not in card_data:
        raise HTTPException(status_code=404, detail="해당 카드명을 찾을 수 없습니다.")

    for key in req.update:
        if key in card_data[name]:
            card_data[name][key] = req.update[key]

    save_cards(card_data)
    return {"result": "success", "message": f"{req.name} 카드 수정 완료"}

# 카드 삭제
@app.post("/delete_card")
async def delete_card(req: CardDeleteRequest):
    card_data = load_cards()
    name = req.name.strip()

    if name not in card_data:
        raise HTTPException(status_code=404, detail="해당 카드명을 찾을 수 없습니다.")

    del card_data[name]
    save_cards(card_data)
    return {"result": "success", "message": f"{req.name} 카드 삭제 완료"}

# 카드 JSON 다운로드
@app.get("/download_json")
def download_json():
    json_path = os.path.join(os.getcwd(), CARDS_FILE)
    if os.path.exists(json_path):
        return FileResponse(path=json_path, filename=CARDS_FILE, media_type="application/json")
    else:
        return {"message": "cards.json 파일이 존재하지 않습니다."}

# ✅ DC 마이너갤러리 검색 기능
@app.get("/dcsearch")
def dcsearch(keyword: str = Query(..., description="검색어")):
    encoded_keyword = quote(keyword)
    search_url = f"https://gall.dcinside.com/mgallery/board/lists?id=marvelsnap&s_type=search_subject_memo&s_keyword={encoded_keyword}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        posts = soup.select("tbody tr.us-post")
        results = []

        for post in posts[:3]:
            a_tag = post.select_one(".gall_tit a")
            if a_tag:
                title = a_tag.get("title") or a_tag.get_text(strip=True)
                href = "https://gall.dcinside.com" + a_tag["href"]
                results.append({"title": title, "url": href})

        return JSONResponse(content=results)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
