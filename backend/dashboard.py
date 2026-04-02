import json
from datetime import datetime
from nicegui import ui


class Dashboard:
    def __init__(self, full_config):
        self.full_config = full_config
        self.sensor_ui_labels = {}
        self.is_paid = self.full_config.get("has_subscription", False)
        self.expiry_str = self.full_config.get("expiry_date", "")

        # Mặc định chọn xưởng đầu tiên
        self.selected_factory_data = self.full_config["factories"][0]

        # Cấu hình Header html cho Mobile
        ui.add_head_html(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')
        ui.query('.q-page').classes('bg-slate-50')

        self.build_ui()

    def build_ui(self):
        @ui.page('/')
        async def main_page():
            # --- HEADER ---
            with ui.header().classes('bg-blue-900 items-center justify-between'):
                ui.label('🏭 IIoT Global Manager').classes('text-h5 text-white')

            with ui.column().classes('w-full p-4 gap-2'):
                # --- CARD THÔNG TIN TÀI KHOẢN ---
                with ui.card().classes('w-full shadow-none border p-2 bg-slate-50'):
                    self._render_subscription_info()

                # --- CHỌN NHÀ XƯỞNG ---
                factory_names = [f["f_name"] for f in self.full_config["factories"]]
                ui.select(factory_names, value=factory_names[0], label='📍 Chọn Nhà xưởng/Vị trí:',
                          on_change=self._change_factory).classes('w-full md:w-1/3')

                # --- NỘI DUNG CHÍNH ---
                self.content_container = ui.column().classes('w-full')
                self._render_main_content()

    def _render_subscription_info(self):
        with ui.row().classes('w-full items-start justify-between'):
            with ui.column().classes('col-grow'):
                if not self.is_paid:
                    ui.markdown('##### 🔓 Tài khoản: **Bản miễn phí (Local Only)**').classes('m-0')
                    ui.label('Chỉ giám sát trong mạng nội bộ.').classes('text-grey-7 text-caption')
                else:
                    expiry_date = datetime.strptime(self.expiry_str, "%Y-%m-%d")
                    days_left = (expiry_date - datetime.now()).days
                    ui.markdown(f'### 🛡️ Tài khoản: **PRO (Remote Cloud)**').classes('m-0')
                    color = 'blue' if days_left > 0 else 'red'
                    with ui.row().classes(f'items-center bg-{color}-50 p-2 rounded w-full'):
                        ui.icon('info' if days_left > 0 else 'warning', color=color)
                        ui.label(f'📅 Thời hạn: {days_left} ngày').classes(f'text-{color}-900')

            with ui.column().classes('w-full md:w-1/4 items-end'):
                btn_label = '🚀 ĐĂNG KÝ CLOUD' if not self.is_paid else '🔄 GIA HẠN'
                ui.button(btn_label, on_click=self._show_subscription_options).props('primary unelevated').classes(
                    'w-full h-12')

    @ui.refreshable
    def _render_main_content(self):
        f_data = self.selected_factory_data
        with ui.tabs().props('align="left"').classes('w-full bg-white border-b') as tabs:
            t1 = ui.tab('📊 Giám sát')
            t2 = ui.tab('🎮 Điều khiển')

        with ui.tab_panels(tabs, value=t1).classes('w-full bg-transparent'):
            with ui.tab_panel(t1):
                for gw in f_data["gateways"]:
                    ui.label(f"📡 Gateway: {gw['gw_id']}").classes('text-grey-7 mt-2')
                    with ui.row().classes('w-full gap-4'):
                        sensors = [d for d in gw["devices"] if d["type"] == "sensor"]
                        for s in sensors:
                            # TẠO CARD SENSOR VÀ LƯU REFERENCE
                            card = ui.card().classes('w-40 items-center p-4')
                            with card:
                                ui.icon(s.get('icon', 'sensors'), size='md', color='blue')
                                ui.label(s['label']).classes('text-caption')
                                # Lưu object label vào dict để update sau này
                                label_obj = ui.label('--').classes('text-xl font-bold')

                                # Đăng ký vào mapping để Backend tìm thấy
                                s_id = s.get('id', s['label'])  # Ưu tiên ID nếu có
                                self.sensor_ui_labels[s_id] = {
                                    'label_obj': label_obj,
                                    'unit': s.get('unit', '')
                                }

    def update_ui_data(self, iot_values: list):
        """
        Hàm này sẽ được IoTBackend gọi trực tiếp khi có dữ liệu mới.
        iot_values: [temp, humi]
        """
        try:
            # Cập nhật Nhiệt độ (ID: temp_01)
            if 'temp_01' in self.sensor_ui_labels:
                item = self.sensor_ui_labels['temp_01']
                item['label_obj'].set_text(f"{iot_values[0]} {item['unit']}")

            # Cập nhật Độ ẩm (ID: humi_01)
            if 'humi_01' in self.sensor_ui_labels:
                item = self.sensor_ui_labels['humi_01']
                item['label_obj'].set_text(f"{iot_values[1]} {item['unit']}")
        except Exception as e:
            print(f"UI Update Error: {e}")

    def _change_factory(self, e):
        self.selected_factory_data = next(f for f in self.full_config["factories"] if f["f_name"] == e.value)
        self._render_main_content.refresh()

    async def _show_subscription_options(self):
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('💎 Nâng cấp gói').classes('text-h6')
            ui.button('Đóng', on_click=dialog.close).classes('w-full mt-4')
        dialog.open()
