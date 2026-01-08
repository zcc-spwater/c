import os
import json
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 定義 app (解決 NameError 的關鍵) ---
app = Flask(__name__)

# --- 2. 設定 Google Sheets 連線 ---
google_json = os.environ.get('GOOGLE_SHEETS_JSON')

if google_json:
    creds_dict = json.loads(google_json)
    creds = Credentials.from_service_account_info(creds_dict)
    client = gspread.authorize(creds)
else:
    # 本地開發備用
    client = gspread.service_account(filename='credentials.json')

# 使用你的試算表 ID
spreadsheet = client.open_by_key("1Xb_tjeB3KbuXSxlwCwVsthRhAPIMKU8SYeiMMkyuEhw")
sheet = spreadsheet.worksheet("工作表1")

# --- 3. 網頁路徑 ---

@app.route("/")
def index():
    # 讀取排行榜資料
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    data = leader_sheet.get_all_records()
    
    # 依照「積分」排序
    sorted_data = sorted(data, key=lambda x: int(x['積分']), reverse=True) if data else []
    
    # 取前 10 名
    display_list = [{"name": row['姓名'], "score": row['積分']} for row in sorted_data[:10]]
    
    return render_template("index.html", leaderboard=display_list)

@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form["student_id"]
    name = request.form["name"]
    date = request.form["date"]
    status = request.form["status"]
    
    # 積分規則
    points = {"出席": 10, "公假": 10, "遲到": 5, "病假": 0, "事假": 0, "缺席": -5}
    current_points = points.get(status, 0)
    
    # 寫入紀錄
    sheet.append_row([student_id, name, date, status])
    
    # 更新排行榜
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    cell = leader_sheet.find(student_id)
    
    if cell:
        row = cell.row