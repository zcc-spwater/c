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
            # 1. 取得學號並移除空格
            sid = str(row.get('學號', '')).strip()
            if not sid: continue 
            
            # 2. 取得姓名
            name = str(row.get('姓名', '未知')).strip()
            
            # 3. 超強防呆積分處理：如果是空的或非數字，直接給 0 分
            raw_val = row.get('積分', 0)
            try:
                # 只保留數字字元
                clean_val = "".join(filter(str.isdigit, str(raw_val)))
                score = int(clean_val) if clean_val else 0
            except:
                score = 0
            
            # 4. 根據學號合計
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 5. 排序並傳回
        leaderboard = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"讀取排行榜失敗：{e}"
        # force_update_v99