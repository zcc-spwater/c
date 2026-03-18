@app.route("/")
def index():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        all_records = sheet.get_all_records()

        summary = {} 
        for row in all_records:
            # 1. 取得學號並移除空格，如果學號為空就跳過
            sid = str(row.get('學號', '')).strip()
            if not sid: continue 
            
            # 2. 取得姓名
            name = str(row.get('姓名', '未知')).strip()
            
            # 3. 關鍵防呆：處理「空值」或「非數字」導致的 ValueError
            raw_score = row.get('積分', 0)
            try:
                # 只留下數字部分
                score_str = "".join(filter(str.isdigit, str(raw_score)))
                score = int(score_str) if score_str else 0
            except:
                score = 0
            
            # 4. 進行資料加總
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 5. 排序並傳送到前端
        leaderboard_data = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        
        return render_template("index.html", leaderboard=leaderboard_data[:10])
    except Exception as e:
        # 這裡會捕捉並顯示錯誤，方便我們除錯
        return f"讀取排行榜失敗，詳細原因：{e}"