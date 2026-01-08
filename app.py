import os
import json
from datetime import datetime
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# 連線設定
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
google_json = os.environ.get('GOOGLE_SHEETS_JSON')

if google_json:
    creds_dict = json.loads(google_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
else:
    client = gspread.service_account(filename='credentials.json', scopes=scopes)

spreadsheet = client.open_by_key("1Xb_tjeB3KbuXSxlwCwVsthRhAPIMKU8SYeiMMkyuEhw")
sheet = spreadsheet.worksheet("工作表1")

@app.route("/")
def index():
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    data = leader_sheet.get_all_records()
    sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)), reverse=True) if data else []
    display_list = [{"name": row.get('姓名', '未知'), "score": row.get('積分', 0)} for row in sorted_data[:10]]
    return render_template("index.html", leaderboard=display_list)

@app.route("/submit", methods=["POST"])
def submit():
    student_id = str(request.form["student_id"]).strip()
    name = request.form["name"]
    date_str = request.form["date"] # 格式通常是 YYYY-MM-DD
    status = request.form["status"]
    
    # --- 功能 A：一天只能填一次 ---
    # 檢查「工作表1」中是否已有 該學號 + 該日期 的紀錄
    all_records = sheet.get_all_records()
    for record in all_records:
        if str(record.get('學號')) == student_id and str(record.get('日期')) == date_str:
            return f"<h2>抱歉，{name}！你今天已經簽到過了。</h2><p><a href='/'>返回</a></p>"

    # 積分規則
    points_map = {"出席": 10, "公假": 10, "遲到": 5, "病假": 0, "事假": 0, "缺席": -5}
    current_points = points_map.get(status, 0)
    
    # 寫入紀錄
    sheet.append_row([student_id, name, date_str, status])
    
    # 更新排行榜
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    cell = leader_sheet.find(student_id)
    
    if cell:
        row_idx = cell.row
        val = leader_sheet.cell(row_idx, 3).value
        old_score = int(val) if (val and str(val).isdigit()) else 0
        leader_sheet.update_cell(row_idx, 3, old_score + current_points)
    else:
        leader_sheet.append_row([student_id, name, current_points])
    
    return "<h2>簽到成功！分數已更新。</h2><p><a href='/'>返回排行榜</a></p>"

if __name__ == "__main__":
    app.run(debug=True)
    @app.route("/submit", methods=["POST"])
def submit():
    student_id = str(request.form["student_id"]).strip()
    name = request.form["name"]
    date_str = request.form["date"] 
    status = request.form["status"]
    
    # --- 防止一天填多次 ---
    all_records = sheet.get_all_records()
    for record in all_records:
        # 比對學號和日期，如果都一樣就拒絕
        if str(record.get('學號')) == student_id and str(record.get('日期')) == date_str:
            return f"<h2>{name}，你今天已經簽到過了！</h2><p><a href='/'>返回</a></p>"

    # 積分計算與寫入 (這部分維持原樣)
    points_map = {"出席": 10, "公假": 10, "遲到": 5, "病假": 0, "事假": 0, "缺席": -5}
    current_points = points_map.get(status, 0)
    sheet.append_row([student_id, name, date_str, status])
    
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    cell = leader_sheet.find(student_id)
    if cell:
        row_idx = cell.row
        val = leader_sheet.cell(row_idx, 3).value
        old_score = int(val) if (val and str(val).isdigit()) else 0
        leader_sheet.update_cell(row_idx, 3, old_score + current_points)
    else:
        leader_sheet.append_row([student_id, name, current_points])
    
    return "<h2>簽到成功！</h2><p><a href='/'>返回排行榜</a></p>"