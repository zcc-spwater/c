import os
import json
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 初始化 Flask ---
app = Flask(__name__)

# --- 2. 設定 Google Sheets 連線與權限 ---
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

google_json = os.environ.get('GOOGLE_SHEETS_JSON')

if google_json:
    creds_dict = json.loads(google_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
else:
    client = gspread.service_account(filename='credentials.json', scopes=scopes)

# 連線到你的試算表
spreadsheet = client.open_by_key("1Xb_tjeB3KbuXSxlwCwVsthRhAPIMKU8SYeiMMkyuEhw")
sheet = spreadsheet.worksheet("工作表1")

# --- 3. 網頁路徑設定 ---

@app.route("/")
def index():
    # 讀取排行榜
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    data = leader_sheet.get_all_records()
    # 依照積分排序
    sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)), reverse=True) if data else []
    display_list = [{"name": row.get('姓名', '未知'), "score": row.get('積分', 0)} for row in sorted_data[:10]]
    return render_template("index.html", leaderboard=display_list)

@app.route("/submit", methods=["POST"])
def submit():
    student_id = str(request.form["student_id"]).strip()
    name = request.form["name"]
    date_str = request.form["date"] 
    status = request.form["status"]
    # 接收前端傳來的節次 (第1節~第8節)
    period = request.form.get("period", "第1節") 

    # --- 關鍵功能：防止同一節課重複簽到 ---
    all_records = sheet.get_all_records()
    for record in all_records:
        # 同時檢查：學號、日期、節次。三者都對上才算重複。
        if (str(record.get('學號')) == student_id and 
            str(record.get('日期')) == date_str and 
            str(record.get('節次')) == period):
            return f"<h2>{name}，你這節課（{period}）已經簽到過了！</h2><p><a href='/'>返回</a></p>"

    # 積分規則
    points_map = {"出席": 10, "公假": 10, "遲到": 5, "病假": 0, "事假": 0, "缺席": -5}
    current_points = points_map.get(status, 0)
    
    # 寫入「工作表1」(包含節次)
    sheet.append_row([student_id, name, date_str, period, status])
    
    # 更新「Leaderboard」總積分
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    cell = leader_sheet.find(student_id)
    if cell:
        row_idx = cell.row
        val = leader_sheet.cell(row_idx, 3).value
        old_score = int(val) if (val and str(val).isdigit()) else 0
        leader_sheet.update_cell(row_idx, 3, old_score + current_points)
    else:
        # 如果是新面孔，直接建立資料
        leader_sheet.append_row([student_id, name, current_points])
    
    return f"<h2>簽到成功！{period} 分數已更新。</h2><p><a href='/'>返回排行榜</a></p>"

if __name__ == "__main__":
    app.run(debug=True)