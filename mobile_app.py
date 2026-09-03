import csv
from datetime import datetime
import json
import sqlite3
import urllib.parse
import urllib.request
import webbrowser
import flet as ft


def init_db():
  conn = sqlite3.connect('attendance.db')
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT,
            branch_name TEXT,
            action_type TEXT,
            latitude TEXT,
            longitude TEXT,
            timestamp TEXT
        )
    """)
  conn.commit()
  conn.close()


def get_gps_coordinates():
  try:
    url = 'http://ip-api.com/json/'
    req = urllib.request.urlopen(url, timeout=2)
    data = json.loads(req.read().decode())
    return str(data.get('lat', '21.2854')), str(data.get('lon', '40.4231'))
  except:
    return '21.2854', '40.4231'


def main(page: ft.Page):
  init_db()
  page.title = 'نظام الحضور والانصراف للفروع (مع واتساب)'
  page.rtl = True
  page.vertical_alignment = ft.MainAxisAlignment.CENTER
  page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
  page.padding = 20
  page.theme_mode = ft.ThemeMode.LIGHT

  title_text = ft.Text(
      'إدارة الحضور والانصراف والواتساب',
      size=18,
      weight=ft.FontWeight.BOLD,
      color='blue',
  )

  employee_name_input = ft.TextField(label='اسم الموظف', border_radius=10)

  branch_dropdown = ft.Dropdown(
      label='اختر الفرع الحالي',
      border_radius=10,
      options=[
          ft.dropdown.Option('فرع الرئيسية - المحطة المركزية'),
          ft.dropdown.Option('فرع صيانة شبكات الجهد المتوسط'),
          ft.dropdown.Option('فرع اختبار الكابلات والمحولات'),
          ft.dropdown.Option('فرع اللوحات وقواطع الدائرة'),
      ],
  )

  result_output = ft.Text('', size=13)
  records_list = ft.ListView(expand=1, spacing=5, padding=5, auto_scroll=True)

  def load_records():
    records_list.controls.clear()
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT employee_name, branch_name, action_type, latitude, longitude,'
        ' timestamp FROM attendance ORDER BY id DESC'
    )
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
      action_color = 'green' if row[2] == 'حضور' else 'red'
      action_icon = '🟢' if row[2] == 'حضور' else '🔴'

      records_list.controls.append(
          ft.Card(
              content=ft.Container(
                  content=ft.Column([
                      ft.Row([
                          ft.Text(
                              f'{action_icon} الحالة: {row[2]}',
                              weight=ft.FontWeight.BOLD,
                              color=action_color,
                          ),
                          ft.Text(f'👤 {row[0]}', weight=ft.FontWeight.BOLD),
                      ]),
                      ft.Text(f'🏢 الفرع: {row[1]}', color='grey'),
                      ft.Text(
                          f'📍 GPS: ({row[3]}, {row[4]})',
                          size=11,
                          color='green',
                      ),
                      ft.Text(f'⏰ الوقت: {row[5]}', size=11, color='blue'),
                  ]),
                  padding=8,
              )
          )
      )
    page.update()

  def handle_action(action_type):
    if not employee_name_input.value or not branch_dropdown.value:
      result_output.value = 'الرجاء إدخال اسم الموظف واختيار الفرع من القائمة!'
      result_output.color = 'red'
    else:
      lat, lon = get_gps_coordinates()
      now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

      # حفظ في قاعدة البيانات
      conn = sqlite3.connect('attendance.db')
      cursor = conn.cursor()
      cursor.execute(
          'INSERT INTO attendance (employee_name, branch_name, action_type,'
          ' latitude, longitude, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
          (
              employee_name_input.value,
              branch_dropdown.value,
              action_type,
              lat,
              lon,
              now,
          ),
      )
      conn.commit()
      conn.close()

      # تجهيز رسالة الواتساب التلقائية
      msg = (
          f'📌 *تقرير الحضور والانصراف الميداني*\n\n'
          f'👤 الموظف: {employee_name_input.value}\n'
          f'🏢 الفرع: {branch_dropdown.value}\n'
          f'⚡ الحالة: {action_type}\n'
          f'⏰ الوقت: {now}\n'
          f'📍 الموقع (GPS): https://maps.google.com/?q={lat},{lon}'
      )

      # ترميز الرسالة لفتح الواتساب بشكل صحيح
      encoded_msg = urllib.parse.quote(msg)
      whatsapp_url = f'https://wa.me/?text={encoded_msg}'

      # فتح الواتساب تلقائياً في المتصفح / تطبيق الواتساب
      webbrowser.open(whatsapp_url)

      result_output.value = (
          f'تم تسجيل [{action_type}] وإرسال تفاصيل الواتساب بنجاح! ✅'
      )
      result_output.color = 'green'
      employee_name_input.value = ''
      branch_dropdown.value = None
      load_records()
    page.update()

  check_in_btn = ft.ElevatedButton(
      content=ft.Text('تسجيل حضور وواتساب 🟢', color='white'),
      on_click=lambda e: handle_action('حضور'),
      bgcolor='green',
      width=180,
  )

  check_out_btn = ft.ElevatedButton(
      content=ft.Text('تسجيل انصراف وواتساب 🔴', color='white'),
      on_click=lambda e: handle_action('انصراف'),
      bgcolor='red',
      width=180,
  )

  buttons_column = ft.Column(
      [check_in_btn, check_out_btn],
      horizontal_alignment=ft.CrossAxisAlignment.CENTER,
  )

  def handle_export(e):
    try:
      conn = sqlite3.connect('attendance.db')
      cursor = conn.cursor()
      cursor.execute(
          'SELECT employee_name, branch_name, action_type, latitude, longitude,'
          ' timestamp FROM attendance ORDER BY id DESC'
      )
      rows = cursor.fetchall()
      conn.close()

      with open(
          'attendance_branch_report.csv',
          'w',
          newline='',
          encoding='utf-8-sig',
      ) as f:
        writer = csv.writer(f)
        writer.writerow([
            'اسم الموظف',
            'اسم الفرع',
            'الحالة',
            'خط العرض',
            'خط الطول',
            'وقت التسجيل',
        ])
        writer.writerows(rows)

      result_output.value = 'تم تصدير تقرير الفروع إلى ملف Excel بنجاح! 📊'
      result_output.color = 'green'
    except Exception as ex:
      result_output.value = f'حدث خطأ أثناء التصدير: {ex}'
      result_output.color = 'red'
    page.update()

  export_btn = ft.ElevatedButton(
      content=ft.Text('تصدير السجل الكامل (Excel)', color='white'),
      on_click=handle_export,
      bgcolor='blue',
      width=280,
  )

  load_records()

  page.add(
      ft.Container(
          content=ft.Column(
              [
                  title_text,
                  ft.Divider(height=10),
                  employee_name_input,
                  branch_dropdown,
                  buttons_column,
                  export_btn,
                  result_output,
                  ft.Divider(height=10),
                  ft.Text('📋 سجل الحضور والانصراف:', weight=ft.FontWeight.BOLD),
                  ft.Container(
                      content=records_list,
                      height=150,
                      bgcolor='#f9f9f9',
                      border_radius=10,
                  ),
              ],
              horizontal_alignment=ft.CrossAxisAlignment.CENTER,
              spacing=8,
          ),
          padding=12,
          bgcolor='white',
          border_radius=15,
          width=410,
      )
  )


ft.app(target=main)