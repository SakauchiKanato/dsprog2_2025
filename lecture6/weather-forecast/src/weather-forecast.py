import flet as ft
import requests
import database
from datetime import datetime

AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"

# jsonファイルによっての対応エリアコード変換マップ
AREA_MAPPING = {
    "014030": "014100",  # 十勝地方 -> 釧路・根室地方のファイルに含まれる
    "460040": "460100",  # 奄美 -> 鹿児島県のファイルに含まれる
}

def main(page: ft.Page):
    page.title = "天気予報アプリ (DB対応版)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10

    # DBの初期化
    database.init_db()

    weather_display = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    history_dropdown = ft.Dropdown(
        label="過去の予報を表示",
        width=200,
        on_change=lambda e: show_history(e.control.value),
        visible=False
    )
    current_area_code = None

    def save_area_data():
        try:
            res = requests.get(AREA_URL)
            res.raise_for_status()
            area_data = res.json()
            offices = area_data["offices"]
            for code, info in offices.items():
                database.save_area(code, info["name"])
            
            # 各支庁の中にある「地域（Area）」のデータも保存しておく必要がある
            # これをしないと、予報データ表示時の名称取得でJOINに失敗する
            centers = area_data["centers"]
            for c_code, c_info in centers.items():
                if "children" in c_info:
                    # centers にも offices と同様のコードが含まれる場合があるが、
                    # 重要なのは予報JSONに含まれる地域の名称
                    pass
            
            # 実際には予報JSONに含まれる地域の情報は別途保存するか、
            # officesテーブルにマウントされている全地域（class10など）を網羅する必要がある
            # ここでは簡単のため、JSON取得時に動的に保存する形も併用する
        except Exception as e:
            print(f"Error saving area data: {e}")

    # 初回起動時にエリア情報をDBに保存
    save_area_data()

    def get_weather(e):
        nonlocal current_area_code
        # クリックされたボタンの支庁コード
        original_office_code = e.control.data['code']
        region_name = e.control.data['name']
        current_area_code = original_office_code

        # マップにあれば変換後のコードを取得先とする
        target_office_code = AREA_MAPPING.get(original_office_code, original_office_code)

        weather_display.controls.clear()
        weather_display.controls.append(ft.ProgressBar(width=None))
        weather_display.controls.append(ft.Text(f"{region_name} のデータを取得中...", size=20))
        page.update()

        try:
            url = FORECAST_URL_TEMPLATE.format(code=target_office_code)
            res = requests.get(url)
            res.raise_for_status()
            weather_data = res.json()

            report = weather_data[0]
            report_datetime = report["reportDatetime"]
            ts_weather = report["timeSeries"][0]
            ts_pop = report["timeSeries"][1] if len(report["timeSeries"]) > 1 else None

            # データをDBに保存
            for area_data in ts_weather["areas"]:
                sub_area_code = area_data["area"]["code"]
                sub_area_name = area_data["area"]["name"]
                
                # エリア名もDBに保存（表示用）
                database.save_area(sub_area_code, sub_area_name)
                
                weathers = area_data.get("weathers", [])
                
                # 降水確率の取得
                pops = []
                if ts_pop:
                    same_area_pop = next((x for x in ts_pop["areas"] if x["area"]["code"] == sub_area_code), None)
                    if same_area_pop:
                        pops = same_area_pop.get("pops", [])
                
                time_defines = ts_weather["timeDefines"]
                
                for idx, w_text in enumerate(weathers):
                    target_date = time_defines[idx][:10] # YYYY-MM-DD
                    pop_val = int(pops[idx]) if len(pops) > idx and pops[idx] else None
                    # office_code (target_office_code) も一緒に保存
                    database.save_forecast(target_office_code, sub_area_code, report_datetime, target_date, w_text, pop_val)

            # DBからデータを取得して表示
            display_weather_from_db(target_office_code, original_office_code, region_name)
            
            # 履歴ドロップダウンの更新
            update_history_dropdown(target_office_code)

        except Exception as err:
            weather_display.controls.clear()
            weather_display.controls.append(ft.Text(f"データ取得エラー: {err}", color=ft.Colors.RED))
            page.update()

    def display_weather_from_db(office_code, original_clicked_code, region_name, specific_date=None):
        weather_display.controls.clear()
        
        # タイトル表示
        title_text = f"{region_name}周辺の予報"
        if specific_date:
            title_text += f" ({specific_date} 時点の記録)"
            
        weather_display.controls.append(
            ft.Container(
                content=ft.Text(title_text, size=28, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(bottom=10)
            )
        )

        dates_to_show = []
        if specific_date:
            dates_to_show = [specific_date]
        else:
            from datetime import timedelta
            today = datetime.now()
            dates_to_show = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]

        # 日付ごとに情報をまとめる
        for date_str in dates_to_show:
            results = database.get_forecasts_by_office_and_date(office_code, date_str)
            if not results:
                continue

            # 日付見出し
            weather_display.controls.append(
                ft.Text(f"【{date_str}】", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY)
            )

            # エリアごとのカードを表示
            for area_code, area_name, weather, pop, report_dt in results:
                is_selected = (area_code == original_clicked_code)
                pop_text = f" / 降水確率: {pop}%" if pop is not None else ""
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.BLUE if is_selected else ft.Colors.GREY),
                                    title=ft.Text(f"{area_name}", size=18, weight=ft.FontWeight.BOLD if is_selected else None),
                                    subtitle=ft.Text(f"{weather}{pop_text}"),
                                ),
                            ]
                        ),
                        padding=5,
                        border=ft.border.all(color=ft.Colors.BLUE, width=2) if is_selected else None
                    ),
                    elevation=2 if is_selected else 1
                )
                weather_display.controls.append(card)

        if not weather_display.controls or len(weather_display.controls) <= 1:
            weather_display.controls.append(ft.Text("データが見つかりませんでした。", color=ft.Colors.GREY))
            
        page.update()

    def update_history_dropdown(office_code):
        dates = database.get_historical_dates_by_office(office_code)
        if dates:
            history_dropdown.options = [ft.dropdown.Option(d) for d in dates]
            history_dropdown.visible = True
        else:
            history_dropdown.visible = False
        page.update()

    def show_history(selected_date):
        if current_area_code and selected_date:
            # 地域名を取得
            areas = database.get_areas()
            region_name = next((name for code, name in areas if code == current_area_code), "不明な地域")
            target_office_code = AREA_MAPPING.get(current_area_code, current_area_code)
            display_weather_from_db(target_office_code, current_area_code, region_name, specific_date=selected_date)

    # --- サイドバー構築 ---
    sidebar_content = [
        ft.Text("地域選択", size=20, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        history_dropdown,
        ft.Divider(),
    ]
    try:
        area_data = requests.get(AREA_URL).json()
        centers = area_data["centers"]
        offices = area_data["offices"]

        for center_code, center_info in centers.items():
            child_tiles = []
            for office_code in center_info["children"]:
                if office_code in offices:
                    office_name = offices[office_code]["name"]
                    tile = ft.ListTile(
                        title=ft.Text(office_name),
                        on_click=get_weather,
                        data={"code": office_code, "name": office_name}
                    )
                    child_tiles.append(tile)
            
            expansion_tile = ft.ExpansionTile(
                title=ft.Text(center_info["name"]),
                controls=child_tiles,
                collapsed_text_color=ft.Colors.BLACK87,
                text_color=ft.Colors.BLUE,
            )
            sidebar_content.append(expansion_tile)

    except Exception as e:
        sidebar_content.append(ft.Text(f"エリア定義エラー: {e}"))

    page.add(
        ft.Row(
            [
                ft.Container(
                    width=300,
                    content=ft.ListView(controls=sidebar_content, expand=True),
                    border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.GREY_300)),
                ),
                ft.Container(
                    content=weather_display,
                    expand=True,
                    padding=20,
                    alignment=ft.alignment.top_left,
                    bgcolor=ft.Colors.GREY_100 
                ),
            ],
            expand=True,
        )
    )

ft.app(target=main)