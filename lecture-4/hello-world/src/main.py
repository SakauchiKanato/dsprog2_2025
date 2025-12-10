import flet as ft

# カウンター表示用のテキスト
def main(page: ft.Page):
    counter = ft.Text("0", size=50, data=0)

    # ボタンが押下された時に呼び出される関数
    def increment_click(e):
        counter.data += 1
        counter.value = str(counter.data)
        counter.update()

    def decrement_click(e):
        counter.data -= 1
        counter.value = str(counter.data)
        counter.update()


    # カウンターを増やすボタン
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, on_click=increment_click
    )

    # SafeAreaで囲んで、中央にカウンターを配置
    page.add(
        ft.SafeArea(
            ft.Container(
                counter,
                alignment=ft.alignment.center,
            ),
            expand=True,
        ),
        ft.FloatingActionButton(
        icon=ft.Icons.REMOVE, on_click=decrement_click
    ),
    hoge,

    )


ft.app(main)
