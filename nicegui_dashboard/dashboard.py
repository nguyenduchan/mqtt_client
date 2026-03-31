from nicegui import ui
import json
import pandas as pd
from datetime import datetime
import httpx
import os

# Địa chỉ API của FastAPI
BACKEND_URL = os.getenv("BACKEND_URL", "http://local-backend:8001")

sensor_ui_labels = {}
async def update_sensor_values():
    try:
        async with httpx.AsyncClient() as client:
            # Thay URL bằng địa chỉ Backend của bạn
            response = await client.get(f"{BACKEND_URL}/get-data")
            if response.status_code == 200:
                full_data = response.json()
                # Lấy dict sensor/data (chứa {temperature: 25, humidity: 60})
                iot_values = full_data.get("sensor/data", {})
                
                # Cập nhật Nhiệt độ (giả sử ID sensor nhiệt độ là 'temp_01')
                if 'temp_01' in sensor_ui_labels:
                    item = sensor_ui_labels['temp_01']
                    item['label_obj'].set_text(f"{iot_values[0]} {item['unit']}")
                
                # Cập nhật Độ ẩm (giả sử ID sensor độ ẩm là 'humi_01')
                if 'humi_01' in sensor_ui_labels:
                    item = sensor_ui_labels['humi_01']
                    item['label_obj'].set_text(f"{iot_values[1]} {item['unit']}")
                    sensor_ui_labels["gauge"]['label_obj'].options['series'][0]['data'][0]['value'] = iot_values[1]
                    #sensor_ui_labels["gauge"]['label_obj'].update()
                    
    except Exception as e:
        print(f"Lỗi update: {e}")

# Chạy timer cập nhật mỗi 2 giây
ui.timer(2.0, update_sensor_values)

# Thêm meta tag để chặn user-scalable và ép initial-scale
ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">')

# --- LOAD CONFIG ---
def load_full_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


full_config = load_full_config()
is_paid = full_config.get("has_subscription", False)
expiry_str = full_config.get("expiry_date", "")

# --- CẤU HÍNH GIAO DIỆN ---
ui.query('.q-page').classes('bg-slate-50')  # Màu nền nhẹ


# --- DIALOG NÂNG CẤP ---
async def show_subscription_options():
    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label('💎 Nâng cấp gói Remote Cloud').classes('text-h6')
        ui.label('Mở khóa toàn bộ tính năng: Điều khiển từ xa, Lập lịch...')

        prices = {"1 Tháng": "100k", "6 Tháng": "500k", "1 Năm": "900k"}
        with ui.row().classes('w-full justify-around'):
            for period, price in prices.items():
                with ui.card().classes('items-center p-2 cursor-pointer'):
                    ui.label(period).classes('text-bold')
                    ui.label(price)
                    ui.button('CHỌN', on_click=lambda p=period: ui.notify(f'Đã chọn {p}')).props('flat')
        ui.button('Đóng', on_click=dialog.close).classes('w-full mt-4')
    dialog.open()


# --- HEADER & TRẠNG THÁI ---
with ui.header().classes('bg-blue-900 items-center justify-between'):
    ui.label('🏭 IIoT Global Manager').classes('text-h5 text-white')

with ui.column().classes('w-full p-4 gap-2'):
    with ui.card().classes('w-full shadow-none border p-2 bg-slate-50'):
        with ui.row().classes('w-full items-start justify-between'):
            # Cột bên trái (c1 - Thông tin)
            with ui.column().classes('col-grow'):
                if not is_paid:
                    ui.markdown('##### 🔓 Tài khoản: **Bản miễn phí (Local Only)**') \
                        .classes('m-0 text-slate-900 block')
                    ui.label('Bạn chỉ có thể giám sát thiết bị khi ở trong mạng nội bộ của xưởng.').classes(
                        'text-grey-7 text-caption')
                else:
                    # Tính toán ngày còn lại
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                    days_left = (expiry_date - datetime.now()).days

                    ui.markdown(f'### 🛡️ Tài khoản: **PRO (Remote Cloud)**').classes('m-0')

                    if days_left > 0:
                        with ui.row().classes('items-center bg-blue-50 p-2 rounded w-full'):
                            ui.icon('info', color='blue')
                            ui.label(f'📅 Thời hạn còn lại: {days_left} ngày (Hết hạn: {expiry_str})').classes(
                                'text-blue-900')
                    else:
                        with ui.row().classes('items-center bg-red-50 p-2 rounded w-full'):
                            ui.icon('warning', color='red')
                            ui.label('⚠️ Gói thuê bao đã hết hạn. Vui lòng gia hạn.').classes('text-red-900')

            # Cột bên phải (c2 - Nút bấm)
            with ui.column().classes('w-full md:w-1/4 items-end'):
                if not is_paid:
                    ui.button('🚀 ĐĂNG KÝ CLOUD', on_click=show_subscription_options) \
                        .props('primary unelevated') \
                        .classes('w-full h-12 text-bold')
                else:
                    ui.button('🔄 GIA HẠN', on_click=show_subscription_options) \
                        .props('outline color=primary') \
                        .classes('w-full h-12')
                    

def get_gauge_options(value):
    return {
        'series': [{
            'type': 'gauge',
            'min': 0,               # <--- Giá trị nhỏ nhất
            'max': 150,             # <--- Giá trị lớn nhất mới
            'radius': '100%',        # Thu nhỏ vòng tròn so với khung chứa
            'startAngle': 210,
            'endAngle': -30,
            'progress': {'show': True, 'width': 8}, # Đường tiến trình mỏng hơn
            'axisLine': {'lineStyle': {'width': 8}},
            'axisTick': {'show': False},            # Ẩn các vạch chia nhỏ cho đỡ rối
            'splitLine': {'length': 5, 'lineStyle': {'width': 2, 'color': '#999'}},
            'axisLabel': {'distance': 10, 'color': '#999', 'fontSize': 10},
            'anchor': {'show': True, 'size': 10, 'itemStyle': {'color': '#37a2da'}},
            'title': {'offsetCenter': [0, '70%'], 'fontSize': 12}, # Chữ RH nằm dưới
            'detail': {
                'valueAnimation': True,
                'formatter': '{value}%',
                'offsetCenter': [0, '35%'], # Vị trí con số %
                'fontSize': 20              # Chữ số nhỏ lại
            },
            'data': [{'value': value, 'name': 'Độ ẩm'}]
        }]
    }

# --- CHỌN NHÀ XƯỞNG ---
factory_names = [f["f_name"] for f in full_config["factories"]]
selected_factory = {"data": full_config["factories"][0]}  # Default xưởng đầu tiên


def change_factory(e):
    selected_factory["data"] = next(f for f in full_config["factories"] if f["f_name"] == e.value)
    render_content.refresh()


with ui.row().classes('w-full'):
    ui.select(factory_names, value=factory_names[0], label='📍 Chọn Nhà xưởng/Vị trí:', on_change=change_factory).classes(
        'w-full md:w-1/3')


# --- NỘI DUNG CHÍNH (DYNAMIC REFRESH) ---
@ui.refreshable
def render_content():
    f_data = selected_factory["data"]

    # Thêm .props('align="left"') để ép các tab về bên trái
    with ui.tabs().props('align="left"').classes('w-full bg-white border-b') as tabs:
        t1 = ui.tab('📊 Giám sát')
        t2 = ui.tab('🎮 Điều khiển')
        t3 = ui.tab('📹 Camera')
        t4 = ui.tab('📅 Lập lịch')
        t5 = ui.tab('🤖 Tự động hóa')
        t6 = ui.tab('⚠️ Nhật ký')
        t7 = ui.tab('🎧 Hỗ trợ')

    with ui.tab_panels(tabs, value=t1).classes('w-full bg-transparent'):
        # TAB GIÁM SÁT
        with ui.tab_panel(t1):
            for gw in f_data["gateways"]:
                ui.label(f"📡 Gateway: {gw['gw_id']}").classes('text-grey-7 mt-2')
                with ui.row().classes('w-full gap-4'):
                    sensors = [d for d in gw["devices"] if d["type"] == "sensor"]
                    for s in sensors:
                        with ui.card().classes('w-40 items-center p-4'):
                            ui.icon(s.get('icon', 'sensors'), size='md', color='blue')
                            ui.label(s['label']).classes('text-caption')
                            # Trong thực tế dùng ui.timer để cập nhật số này
                            
                            # TẠO LABEL VÀ LƯU VÀO DICT
                            # Gán giá trị mặc định là "--"
                            display_label = ui.label(f"-- {s['unit']}").classes('text-h6 text-bold')
                            sensor_ui_labels[s['id']] = {
                                'label_obj': display_label,
                                'unit': s['unit']
                            }

                    with ui.row().classes('gap-4'):
                        # Card nhỏ gọn
                        with ui.card().classes('p-2 items-center shadow-sm').style('width: 220px; height: 200px'):
                            #ui.label('Độ ẩm').classes('text-xs font-bold text-gray-500')
        
                            # QUAN TRỌNG: .style('width: 120px; height: 120px') sẽ ép background trắng nhỏ lại
                            gauge = ui.echart(get_gauge_options(45)).style('width: 220px; height: 220px')
                            sensor_ui_labels["gauge"] = {
                                'label_obj': gauge,
                                'unit': "Bar"
                            }

        # TAB ĐIỀU KHIỂN
        with ui.tab_panel(t2):
            for gw in f_data["gateways"]:
                controls = [d for d in gw["devices"] if d["type"] == "control"]
                for c in controls:
                    with ui.card().classes('w-full mb-2 p-2'):
                        with ui.row().classes('w-full items-center justify-between'):
                            ui.label(f"**{c['label']}**").classes('text-subtitle1')
                            ui.switch(on_change=lambda e, name=c['label']: ui.notify(f'Đã chuyển {name}'))

        # TAB CAMERA
        with ui.tab_panel(t3):
            if not is_paid:
                with ui.column().classes('w-full items-center p-10 bg-white shadow-sm'):
                    ui.label('Tính năng này chỉ hoạt động trong mạng nội bộ').classes(
                        'text-grey-7')
                    ui.button('Nâng cấp ngay', on_click=show_subscription_options)

            for gw in f_data["gateways"]:
                cameras = [d for d in gw["devices"] if d["type"] == "camera"]
                for cam in cameras:
                    with ui.card().classes('w-full'):
                        ui.label(cam['label'])
                        # Sử dụng url từ config, dùng interactive_image để tối ưu
                        ui.interactive_image(cam['url']).classes('w-full h-64')

        # TAB NÂNG CAO (WALL)
        with ui.tab_panel(t4):
            ui.label('📅 Lập lịch vận hành thông minh').classes('text-h6 mb-2')

            # Dữ liệu ban đầu
            columns = [
                {'name': 'time', 'label': 'Giờ', 'field': 'time', 'align': 'left'},
                {'name': 'cmd', 'label': 'Lệnh', 'field': 'cmd', 'align': 'center'},
                {'name': 'device', 'label': 'Thiết bị', 'field': 'device', 'align': 'left'},
                {'name': 'delete', 'label': 'Xóa', 'field': 'delete'},
            ]

            rows = [
                {'id': 0, 'time': '08:00', 'cmd': 'ON', 'device': 'Bơm Cao Áp'},
                {'id': 1, 'time': '17:00', 'cmd': 'OFF', 'device': 'Hệ thống Đèn'},
            ]

            # Tạo bảng có khả năng tùy biến nội dung (slot)
            with ui.table(columns=columns, rows=rows, row_key='id').classes('w-full shadow-sm') as table:
                # Thêm nút xóa cho mỗi dòng (tương đương num_rows="dynamic")
                table.add_slot('body-cell-delete', '''
                       <q-td :props="props">
                           <q-btn flat round dense icon="delete" color="red" @click="$parent.$emit('delete', props.row)" />
                       </q-td>
                   ''')
                table.on('delete', lambda msg: rows.remove(msg.args) or table.update())

            # Nút thêm dòng mới
            with ui.row().classes('mt-4 justify-between w-full'):
                ui.button('➕ Thêm lịch mới', on_click=lambda: (
                    rows.append({'id': len(rows), 'time': '00:00', 'cmd': 'ON', 'device': 'Thiết bị mới'}),
                    table.update()
                )).props('outline dense')

                ui.button('💾 LƯU CẤU HÌNH', on_click=lambda: ui.notify('Đã lưu lịch vận hành!')).props(
                    'unelevated color=green')

        with ui.tab_panel(t5):
            if not is_paid:
                with ui.column().classes('w-full items-center p-10 bg-white shadow-sm'):
                    ui.icon('lock', size='lg', color='grey')
                    ui.label('Tính năng này yêu cầu gói PRO').classes('text-h6')
                    ui.button('Nâng cấp ngay', on_click=show_subscription_options)
                    ui.label('Hỗ trợ lập trình tự động theo các điều kiện logic').classes(
                        'text-grey-7 mt-2')
            else:
                ui.icon('unlock', size='lg', color='grey')
                ui.label('Tính năng này đã cho phép').classes('text-h6')

        with ui.tab_panel(t6):
            if not is_paid:
                with ui.column().classes('w-full items-center p-10 bg-white shadow-sm'):
                    ui.icon('lock', size='lg', color='grey')
                    ui.label('Tính năng này yêu cầu gói PRO').classes('text-h6')
                    ui.button('Nâng cấp ngay', on_click=show_subscription_options)
                    ui.label('Tính năng này cho phép xem các sự kiện và cảnh báo lỗi trong thời gian dài').classes('text-grey-7')
            else:
                ui.label('📜 Nhật ký hệ thống').classes('text-h6')
                columns = [
                    {'name': 'Time', 'label': 'Thời gian', 'field': 'Time'},
                    {'name': 'Event', 'label': 'Sự kiện', 'field': 'Event'},
                ]
                rows = [
                    {'Time': '10:00', 'Event': 'Lò hơi quá nhiệt'},
                    {'Time': '09:30', 'Event': 'Gateway kết nối lại'}
                ]
                ui.table(columns=columns, rows=rows, row_key='Time').classes('w-full')

        with ui.tab_panel(t7):
            with ui.column().classes('w-full items-center gap-4 p-4'):
                ui.label('🎧 TRUNG TÂM HỖ TRỢ KỸ THUẬT').classes('text-h6 font-bold text-blue-900')
                ui.label('Chúng tôi luôn sẵn sàng hỗ trợ vận hành hệ thống 24/7').classes('text-grey-7 -mt-4')

                # --- GRID THÔNG TIN LIÊN HỆ ---
                with ui.row().classes('w-full justify-center gap-4'):

                    # Khối Hotline
                    with ui.card().classes('w-64 p-4 items-center shadow-sm border'):
                        ui.icon('local_phone', size='lg', color='green')
                        ui.label('Hotline Kỹ thuật').classes('font-bold')
                        ui.label('0123.456.789').classes('text-lg text-green-700 font-bold')
                        ui.button('GỌI NGAY',
                                  on_click=lambda: ui.run_javascript('window.location.href="tel:0123456789"')) \
                            .props('flat dense')

                    # Khối Zalo/Chat
                    with ui.card().classes('w-64 p-4 items-center shadow-sm border'):
                        ui.icon('chat', size='lg', color='blue')
                        ui.label('Hỗ trợ qua Zalo').classes('font-bold')
                        ui.label('Phản hồi trong 5p').classes('text-caption text-grey')
                        ui.button('NHẮN TIN',
                                  on_click=lambda: ui.run_javascript('window.open("https://zalo.me", "_blank")')) \
                            .props('flat dense color=blue')

                    # Khối Email
                    with ui.card().classes('w-64 p-4 items-center shadow-sm border'):
                        ui.icon('alternate_email', size='lg', color='orange')
                        ui.label('Gửi Email').classes('font-bold')
                        ui.label('support@yourcloud.com').classes('text-caption')
                        ui.button('GỬI THƯ', on_click=lambda: ui.run_javascript(
                            'window.location.href="mailto:support@yourcloud.com"')) \
                            .props('flat dense color=orange')

                # --- PHẦN GỬI YÊU CẦU NHANH (TICKET) ---
                with ui.card().classes('w-full max-w-2xl mt-4 p-6 bg-blue-50 shadow-none'):
                    ui.label('📩 Gửi yêu cầu hỗ trợ nhanh').classes('text-subtitle1 font-bold mb-2')
                    with ui.column().classes('w-full gap-2'):
                        name_input = ui.input('Tên của bạn').classes('w-full bg-white').props('outlined dense')
                        issue_input = ui.textarea('Nội dung sự cố / Yêu cầu').classes('w-full bg-white').props(
                            'outlined')

                        def send_ticket():
                            if not name_input.value or not issue_input.value:
                                ui.notify('Vui lòng nhập đầy đủ thông tin!', type='warning')
                            else:
                                # Logic gửi API lên Remote Server ở đây
                                ui.notify(f'Cảm ơn {name_input.value}! Yêu cầu đã được gửi thành công.',
                                          type='positive')
                                name_input.value = ''
                                issue_input.value = ''

                        ui.button('GỬI YÊU CẦU', on_click=send_ticket).classes('w-full h-10 mt-2').props(
                            'unelevated color=blue-9')

                ui.label('Phiên bản phần mềm: v2.4.1 (Stable)').classes('text-xs text-grey-5 mt-4')


render_content()

ui.run(title='IIoT Manager', port=8080)
