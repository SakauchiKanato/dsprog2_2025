import flet as ft
import requests

AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"

# jsonファイルによっての対応エリアコード変換マップ
AREA_MAPPING = {
    "014030": "014100",  # 十勝地方 -> 釧路・根室地方のファイルに含まれる
    "460040": "460100",  # 奄美 -> 鹿児島県のファイルに含まれる
}

def main(page: ft.Page):
    page.title = "天気予報アプリ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10

    weather_display = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def get_weather(e):
        # クリックされたボタンの元のコードと名前
        original_code = e.control.data['code']
        region_name = e.control.data['name']

        # --- 修正箇所: 変換マップを使って正しいファイル取得先を決める ---
        # マップにあれば変換後のコードを、なければ元のコードを使う
        target_code = AREA_MAPPING.get(original_code, original_code)

        weather_display.controls.clear()
        weather_display.controls.append(ft.ProgressBar(width=None))
        weather_display.controls.append(ft.Text(f"{region_name} のデータを取得中...", size=20))
        page.update()

        try:
            # 変換後のコード(target_code)でURLを作る
            url = FORECAST_URL_TEMPLATE.format(code=target_code)

            res = requests.get(url)
            res.raise_for_status()
            weather_data = res.json()

            report = weather_data[0]
            ts_weather = report["timeSeries"][0]
            ts_pop = report["timeSeries"][1] if len(report["timeSeries"]) > 1 else None

            display_items = []
            
            # タイトル表示
            display_items.append(
                ft.Container(
                    content=ft.Text(f"{region_name}の予報", size=28, weight=ft.FontWeight.BOLD),
                    padding=ft.padding.only(bottom=10)
                )
            )
            
            # --- フィルタリングリング処理（オプション） ---
            # そのJSONに含まれる全地域を表示します
            # 「十勝」をクリックして「釧路」のJSONを読むと、釧路・根室・十勝の3つが表示されます
            
            areas_weather = ts_weather["areas"]
            
            found_target = False 
            
            for area_data in areas_weather:
                sub_area_name = area_data["area"]["name"]
                sub_area_code = area_data["area"]["code"]

                # カード作成処理
                weathers = area_data.get("weathers", [])
                
                # 降水確率の取得
                pops = []
                if ts_pop:
                    same_area_pop = next((x for x in ts_pop["areas"] if x["area"]["code"] == sub_area_code), None)
                    if same_area_pop:
                        pops = same_area_pop.get("pops", [])

                weather_info_rows = []
                for day_idx, w_text in enumerate(weathers):
                    day_label = "今日" if day_idx == 0 else "明日" if day_idx == 1 else "明後日"
                    pop_text = ""
                    if len(pops) > day_idx:
                        pop_text = f" / 降水確率: {pops[day_idx]}%"

                    weather_info_rows.append(
                        ft.Text(f"【{day_label}】 {w_text}{pop_text}", size=16)
                    )

                # カードのデザイン
                # もしクリックした地域と、表示しようとしている地域が一致する場合、枠線を太くする等の強調も可能です
                is_selected_area = (sub_area_code == original_code)
                border_side = ft.BorderSide(3, ft.Colors.BLUE) if is_selected_area else ft.BorderSide(0, ft.Colors.TRANSPARENT)

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.BLUE if is_selected_area else ft.Colors.GREY),
                                    title=ft.Text(sub_area_name, size=20, weight=ft.FontWeight.BOLD),
                                ),
                                ft.Container(
                                    content=ft.Column(weather_info_rows, spacing=5),
                                    padding=ft.padding.only(left=20, right=20, bottom=20)
                                )
                            ]
                        ),
                        padding=5,
                        border=ft.border.all(color=ft.Colors.BLUE, width=2) if is_selected_area else None # 選択した地域を強調
                    ),
                    elevation=2
                )
                display_items.append(card)

            weather_display.controls.clear()
            weather_display.controls.extend(display_items)
            page.update()

        except Exception as err:
            weather_display.controls.clear()
            weather_display.controls.append(ft.Text(f"データ取得エラー: {err}\nURL: {url}", color=ft.Colors.RED))
            page.update()

    # --- サイドバー構築 ---
    sidebar_content = []
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