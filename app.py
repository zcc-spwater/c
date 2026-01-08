@app.route("/")
def index():
    # 讀取排行榜工作表的所有資料
    leader_sheet = spreadsheet.worksheet("Leaderboard")
    data = leader_sheet.get_all_records()
    
    # 依照「積分」由高到低排序
    sorted_data = sorted(data, key=lambda x: int(x['積分']), reverse=True) if data else []
    
    # 只取前 10 名傳給網頁
    display_list = [{"name": row['姓名'], "score": row['積分']} for row in sorted_data[:10]]
    
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