import os
import json
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

# 1. 初始化 Flask (解決 NameError)
app = Flask(__name__)

# 2. 設定 Google Sheets 連線權限 (解決 RefreshError)
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

google_json = os.environ.get('GOOGLE_SHEETS_JSON')

if google_json:
    # 讀取 Render 後台設定的金鑰
    creds_dict = json.loads(google_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
else:
    # 電腦本地測試用的備案
    try:
        client = gspread.service_account(filename='credentials.json', scopes=scopes)
    except:
        client = None

# 3. 打開你的試算表 (使用你目前的 ID)
spreadsheet = client.open_by_key("1Xb_tjeB3KbuXSxlwCwVsthRhAPIMKU8SYeiMMkyuEhw")
sheet = spreadsheet.worksheet("工作表1") # 簽到紀錄分頁

# --- 網頁路線設定 ---

@app.route("/")
def index():
    # 讀取排行榜工作表的所有資料
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    data = leader_sheet.get_all_records()
    
    # 依照「積分」由高到低排序 (確保積分是數字)
    sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)), reverse=True) if data else []
    
    # 只取前 10 名傳給網頁
    display_list = [{"name": row.get('姓名', '未知'), "score": row.get('積分', 0)} for row in sorted_data[:10]]
    
    return render_template("index.html", leaderboard=display_list)

@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form["student_id"]
    name = request.form["name"]
    date = request.form["date"]
    status = request.form["status"]
    
    # 設定積分規則
    points = {"出席": 10, "公假": 10, "遲到": 5, "病假": 0, "事假": 0, "缺席": -5}
    current_points = points.get(status, 0)
    
    # 1. 寫入原始紀錄
    sheet.append_row([student_id, name, date, status])
    
    # 2. 更新排行榜
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    cell = leader_sheet.find(student_id)
    
    if cell:
        # 已有紀錄，更新分數
        row = cell.row
        old_score = int(leader_sheet.cell(row, 3).value or 0)
        leader_sheet.update_cell(row, 3, old_score + current_points)
    else:
        # 新同學，新增一行
        leader_sheet.append_row([student_id, name, current_points])
    
    return "<h2>資料已成功送出!</h2><p><a href='/'>返回排行榜</a></p>"

if __name__ == "__main__":
    app.run(debug=True)