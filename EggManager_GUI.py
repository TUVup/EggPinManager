import json
import sys
import os
import re
import time
import ctypes, pyperclip
from itertools import combinations
from datetime import datetime
import pyautogui
import webbrowser
import requests
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import configparser as cp

current_version = "v1.0.7"
config = cp.ConfigParser()

# Windows API 함수 로드
user32 = ctypes.windll.user32

def config_read():
    if not config.read('config.ini'):
        # print("설정 파일을 찾을 수 없습니다. 새로운 설정 파일을 생성합니다.")
        config['DEFAULT'] = {'pin_file': 'pins.json', 'txt_file': 'pins.txt', 'log_file': 'pin_usage_log.txt'}
        config['SETTING'] = {'auto_update': 'True', 'auto_submit': 'False'}
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        config.read('config.ini')
    return config

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class PinManager:
    def __init__(self):
        self.filename = config["DEFAULT"]['pin_file']
        self.pins = self.load_pins()
        self.txt_filename = config["DEFAULT"]['txt_file']
        self.log_filename = config["DEFAULT"]['log_file']

    def load_pins(self):
        try:
            with open(self.filename, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        
    def show_log(self):
        try:
            with open(self.log_filename, "r") as log_file:
                log = log_file.read()
                log_file.close()
                return log
        except FileNotFoundError:
            return "로그 파일을 찾을 수 없습니다."
        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def save_pins(self):
        with open(self.filename, "w") as file:
            json.dump(self.pins, file, indent=4)
    
    def save_pins_to_txt(self):
        with open(self.txt_filename, "w") as file:
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                file.write(f"{idx}. {pin}: {balance}\n")

    # 로그 파일로부터 PIN과 원금을 사용하여 PIN 목록을 복구하는 함수
    def load_pins_from_log(self):
        try:
            with open(self.log_filename, "r") as log_file:
                log_lines = log_file.readlines()
                for line in log_lines:
                    match = re.search(r'(\d{5}-\d{5}-\d{5}-\d{5}) \[원금: (\d+)\]', line)
                    if match:
                        pin = match.group(1)
                        original_balance = int(match.group(2))
                        self.pins[pin] = original_balance
            self.save_pins()
            self.save_pins_to_txt()
            return "PIN 목록이 성공적으로 복구되었습니다."
        except FileNotFoundError:
            return "로그 파일을 찾을 수 없습니다."
        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def add_pin(self, pin, balance):
        self.pins[pin] = balance
        self.save_pins()
        self.save_pins_to_txt()
        return f"PIN {pin} 추가 완료. 잔액: {balance}"
    
    def format_pin(self, pin):
        if len(pin) == 20 and pin.isdigit():
            return f"{pin[:5]}-{pin[5:10]}-{pin[10:15]}-{pin[15:]}"
        return pin
    
    def unformat_pin(self, formatted_pin):
        return formatted_pin.replace("-", "")

    def is_valid_pin_format(self, pin):
        pattern = re.compile(r'^\d{5}-\d{5}-\d{5}-\d{5}$')
        return bool(pattern.match(pin))

    def delete_pin(self, pin):
        pin = self.format_pin(pin)
        if pin in self.pins:
            del self.pins[pin]
            self.save_pins()
            self.save_pins_to_txt()
            return f"PIN {pin} 삭제 완료."
        return f"PIN {pin}은(는) 존재하지 않습니다."
    
    def update_pin_balance(self, pin, new_balance):
        if pin in self.pins:
            self.pins[pin] = new_balance
            self.save_pins()
            self.save_pins_to_txt()
            return True
        return False

    def get_total_balance(self):
        return sum(self.pins.values())

    def list_pins(self):
        return list(self.pins.items())

    def find_pins_for_amount(self, amount):
        sorted_pins = sorted(self.pins.items(), key=lambda x: x[1])
        selected_pins = []
        total_selected = 0
        best_combination = []
        best_total = 0

        # print("Sorted pins: ", sorted_pins)

        for pin, balance in sorted_pins:
            if total_selected >= amount:
                break
            selected_pins.append((pin, balance))
            total_selected += balance

        if total_selected >= amount and len(selected_pins) <= 5:
            # print("Selected pins: ", selected_pins)
            return selected_pins
        else:
            # 가능한 모든 조합을 고려하여 최적의 조합을 찾음
            for r in range(1, 6):
                for combination in combinations(sorted_pins, r):
                    total = sum(balance for pin, balance in combination)
                    if total >= amount and (best_total == 0 or total < best_total):
                        best_combination = combination
                        best_total = total

            if best_total >= amount:
                # print("Best combination: ", best_combination)
                return best_combination
    
        return []
    
    def pin_check(self, pin):
        pin = self.format_pin(pin)
        for pins in self.pins.keys():
            if pins == pin:
                return 1
        return 0
    
class PinManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = PinManager()
        if config['SETTING']['auto_update'] == 'True':
            # print("자동 업데이트가 활성화되어 있습니다.")
            self.auto_check_for_updates() # 프로그램 실행 시 업데이트 체크
        self.initUI()

    def initUI(self):
        # UI 초기화 및 설정
        self.setWindowTitle(f"EggManager {current_version}")
        # self.setWindowFlag(Qt.WindowStaysOnTopHint)
        # self.setGeometry(300, 300, 600, 400)
        self.setMinimumSize(600, 400)
        ico = resource_path('eggui.ico')
        self.setWindowIcon(QIcon(ico))

        # 메뉴 바 추가
        menubar = self.menuBar()
        # menubar.setStyleSheet("QMenuBar { background-color: #f0f0f0; }")
        settings_menu = menubar.addMenu('설정')

        # 프로그램 정보 액션 추가
        about_action = QAction('프로그램 정보', self)
        about_action.triggered.connect(self.show_about_dialog)
        settings_menu.addAction(about_action)

        # GitHub 릴리즈 페이지 액션 추가
        github_action = QAction('GitHub 페이지', self)
        github_action.triggered.connect(self.open_github_releases)
        settings_menu.addAction(github_action)

        # 로그 확인
        show_log = QAction('로그 보기', self)
        show_log.triggered.connect(self.show_log_file)
        settings_menu.addAction(show_log)

        # 업데이트 액션 추가
        update_action = QAction('업데이트 확인', self)
        update_action.triggered.connect(self.check_for_updates)
        settings_menu.addAction(update_action)
        settings_menu.addSeparator()

        # 자동 업데이트 확인 액션 추가
        settings_update = QAction('실행시 자동 업데이트 확인', self, checkable=True)
        settings_update.setChecked(config['SETTING']['auto_update'] == 'True')
        settings_update.triggered.connect(self.update_settings_change)
        settings_menu.addAction(settings_update)

        # 자동 제출 확인 액션 추가 
        settings_submit = QAction('결제창 자동 최종 결제', self, checkable=True)
        settings_submit.setChecked(config['SETTING']['auto_submit'] == 'True')
        settings_submit.triggered.connect(self.auto_submit_settings_change)
        settings_menu.addAction(settings_submit)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # PIN 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["PIN 번호", "잔액"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_pins)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # 버튼 배치
        button_layout = QHBoxLayout()
        btn_add = QPushButton("PIN 추가", self)
        btn_add.clicked.connect(self.add_pin)
        btn_add.setToolTip("새로운 PIN을 추가합니다.")
        button_layout.addWidget(btn_add)

        btn_delete = QPushButton("PIN 삭제", self)
        btn_delete.clicked.connect(self.delete_pin)
        btn_delete.setToolTip("선택한 PIN을 삭제합니다.")
        button_layout.addWidget(btn_delete)

        btn_use = QPushButton("PIN 자동 사용", self)
        btn_use.clicked.connect(self.use_pins)
        btn_use.setToolTip("선택한 금액을 사용할 수 있는 PIN을 자동으로 사용합니다.")
        button_layout.addWidget(btn_use)

        btn_restore = QPushButton("PIN 복구", self)
        btn_restore.clicked.connect(self.restore_pins)
        btn_restore.setToolTip("로그 파일로부터 PIN 목록을 복구합니다.")
        button_layout.addWidget(btn_restore)

        layout.addLayout(button_layout)

        bottom_layout = QHBoxLayout()
        self.sum = QLabel(f"잔액 : {'{0:,}'.format(self.manager.get_total_balance())}", self)
        bottom_layout.addWidget(self.sum)

        bottom_layout.addStretch(1)

        btn_quit = QPushButton("종료", self)
        btn_quit.clicked.connect(self.close)
        bottom_layout.addWidget(btn_quit)

        layout.addLayout(bottom_layout)

        self.update_table()

    # 프로그램 정보 다이얼로그
    def show_about_dialog(self):
        # 프로그램 정보 대화 상자 표시
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("프로그램 정보")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"EggManager {current_version}"))
        layout.addWidget(QLabel("개발자: TUVup"))
        layout.addWidget(QLabel("이 프로그램은 에그머니 PIN 관리를 위한 도구입니다."))
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        about_dialog.setLayout(layout)
        about_dialog.exec()

    # 금액 입력 다이얼로그
    def amount_input_dialog(self, title="금액 입력"):
        input_dialog = QDialog(self)
        input_dialog.setWindowTitle(title)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("금액을 입력하세요."))
        amount_input = QSpinBox()
        amount_input.setWrapping(True)
        amount_input.setRange(0, 50000)
        amount_input.setValue(0)
        amount_input.selectAll()
        amount_input.setSingleStep(1000)
        layout.addWidget(amount_input)
        amount_radio1 = QRadioButton("1000")
        amount_radio2 = QRadioButton("3000")
        amount_radio3 = QRadioButton("5000")
        amount_radio4 = QRadioButton("10000")
        amount_radio5 = QRadioButton("30000")
        amount_radio6 = QRadioButton("50000")
        amount_radio1.clicked.connect(lambda: amount_input.setValue(1000))
        amount_radio2.clicked.connect(lambda: amount_input.setValue(3000))
        amount_radio3.clicked.connect(lambda: amount_input.setValue(5000))
        amount_radio4.clicked.connect(lambda: amount_input.setValue(10000))
        amount_radio5.clicked.connect(lambda: amount_input.setValue(30000))
        amount_radio6.clicked.connect(lambda: amount_input.setValue(50000))
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(amount_radio1)
        radio_layout.addWidget(amount_radio2)
        radio_layout.addWidget(amount_radio3)
        radio_layout.addWidget(amount_radio4)
        radio_layout.addWidget(amount_radio5)
        radio_layout.addWidget(amount_radio6)
        layout.addLayout(radio_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(input_dialog.accept)
        button_box.rejected.connect(input_dialog.reject)
        layout.addWidget(button_box)
        input_dialog.setLayout(layout)
        if input_dialog.exec() == QDialog.Accepted:
            return amount_input.value(), True
        return None, False
    
    def open_github_releases(self):
        # GitHub 릴리즈 페이지 열기
        webbrowser.open("https://github.com/TUVup/EggPinManager")
    
    def show_log_file(self):
        log = self.manager.show_log()
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("로그")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{log}"))
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        about_dialog.setLayout(layout)
        about_dialog.exec()
    
    
    # 자동 업데이트 설정 변경
    def update_settings_change(self):
        if config['SETTING']['auto_update'] == 'True':
            config['SETTING']['auto_update'] = 'False'
        else:
            config['SETTING']['auto_update'] = 'True'
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    
    def auto_submit_settings_change(self):
        if config['SETTING']['auto_submit'] == 'True':
            config['SETTING']['auto_submit'] = 'False'
        else:
            config['SETTING']['auto_submit'] = 'True'
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)

    # GitHub에서 최신 릴리즈 정보를 확인하고 업데이트 여부를 묻는 기능
    def check_for_updates(self):
        try:
            response = requests.get("https://api.github.com/repos/TUVup/EggPinManager/releases/latest")
            response.raise_for_status()
            latest_version = response.json()["tag_name"]
            if latest_version > current_version:
                reply = QMessageBox.question(self, "업데이트 확인", f"새 버전 {latest_version}이(가) 있습니다. 업데이트 하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    webbrowser.open("https://github.com/TUVup/EggPinManager/releases/latest")
            else:
                QMessageBox.information(self, "업데이트 확인", "현재 최신 버전입니다.")
        except requests.RequestException as e:
            QMessageBox.warning(self, "업데이트 확인 실패", f"업데이트 확인 중 오류가 발생했습니다: {e}")

    # 프로그램 실행 시 자동으로 업데이트를 체크하는 기능
    def auto_check_for_updates(self):
        response = requests.get("https://api.github.com/repos/TUVup/EggPinManager/releases/latest")
        response.raise_for_status()
        latest_version = response.json()["tag_name"]
        if latest_version > current_version:
            reply = QMessageBox.question(self, "업데이트 확인", f"새 버전 {latest_version}이(가) 있습니다. 업데이트 하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                webbrowser.open("https://github.com/TUVup/EggPinManager/releases/latest")
    
    # PIN 목록을 로그 파일로부터 복구하는 함수
    def restore_pins(self):
        reply = QMessageBox.question(self, "PIN 복구", "PIN 목록을 로그 파일로부터 복구하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            result = self.manager.load_pins_from_log()
            QMessageBox.information(self, "PIN 복구", result)
            self.update_table()

    # 테이블 위젯에 컨텍스트 메뉴 추가
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        add_action = QAction("PIN 추가", self)
        add_action.triggered.connect(self.add_pin)
        context_menu.addAction(add_action)

        edit_balance_action = QAction("잔액 수정", self)
        edit_balance_action.triggered.connect(self.edit_selected_pin_balance)
        context_menu.addAction(edit_balance_action)

        delete_action = QAction("PIN 삭제", self)
        delete_action.triggered.connect(self.delete_selected_pin)
        context_menu.addAction(delete_action)

        context_menu.exec(self.mapToGlobal(event.pos()))

    # 테이블에서 선택된 핀을 삭제하는 기능
    def delete_selected_pin(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if cancel == QMessageBox.Yes:
                pin = selected_items[0].text()
                result = self.manager.delete_pin(pin)
                QMessageBox.information(self, "결과", result)
                self.update_table()
    
    # 테이블에서 선택된 핀의 잔액을 수정하는 기능
    def edit_selected_pin_balance(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            pin = selected_items[0].text()
            # new_balance, ok = QInputDialog.getInt(self, "잔액 수정", "새 잔액 입력:", 0)
            new_balance, ok = self.amount_input_dialog('잔액 수정')
            if not ok:
                QMessageBox.warning(self, "취소", "잔액 수정이 취소되었습니다.")
                return
            if ok and new_balance <= 0:
                QMessageBox.warning(self, "오류", "잔액은 0보다 커야 합니다.")
                return
            if ok:
                result = self.manager.update_pin_balance(pin, new_balance)
                QMessageBox.information(self, "성공", "잔액 수정이 완료되었습니다.")
                self.update_table()

    # 테이블을 업데이트하는 기능
    def update_table(self):
        self.sum.setText(f"잔액 : {'{0:,}'.format(self.manager.get_total_balance())}")
        pins = self.manager.list_pins()
        self.table.setRowCount(len(pins))
        for row, (pin, balance) in enumerate(pins):
            self.table.setItem(row, 0, QTableWidgetItem(pin))
            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)# | Qt.AlignVCenter
            self.table.setItem(row, 1, QTableWidgetItem('{0:,}'.format(balance)))
            self.table.item(row, 1).setTextAlignment(Qt.AlignCenter)
    
    sort_flag = 0
    
    def sort_pins(self):
        """잔액을 기준으로 PIN 목록을 정렬하는 함수"""
        if self.sort_flag == 0:
            self.manager.pins = dict(sorted(self.manager.pins.items(), key=lambda x: x[1]))
            self.sort_flag = 1
        else:
            self.manager.pins = dict(sorted(self.manager.pins.items(), key=lambda x: x[1], reverse=True))
            self.sort_flag = 0
        self.update_table()

    # PIN 추가 다이얼로그
    def add_pin(self):
        pin, ok = QInputDialog.getText(self, "PIN 추가", "PIN 입력 (핀 전체 또는 숫자만 입력):")
        pin = self.manager.format_pin(pin)
        if self.manager.pin_check(pin) == 1:
            QMessageBox.warning(self, "PIN오류", "중복된 PIN입니다.")
        elif not self.manager.is_valid_pin_format(pin) and ok:
            QMessageBox.warning(self, "오류", "올바른 PIN 형식이 아닙니다.")
        elif ok and pin:
            balance, ok = self.amount_input_dialog()
            if ok and balance > 0:
                result = self.manager.add_pin(pin, balance)
                QMessageBox.information(self, "결과", result)
                self.update_table()
            elif ok and balance <= 0:
                QMessageBox.warning(self, "금액 오류", "0보다 작은 금액은 입력할 수 없습니다.")
            elif ok and not balance:
                QMessageBox.warning(self, "금액 오류", "금액은 반드시 입력해야 합니다.")

    # PIN 삭제 다이얼로그
    def delete_pin(self):
        pin, ok = QInputDialog.getText(self, "PIN 삭제", "삭제할 PIN 입력:")
        if ok and pin:
            if 0 == self.manager.pin_check(pin):
                QMessageBox.warning(self, "PIN오류", "존재하지 않는 PIN입니다.")
            else:
                cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
                if cancel == QMessageBox.Yes:
                    result = self.manager.delete_pin(pin)
                    QMessageBox.information(self, "결과", result)
                    self.update_table()

    # PIN 자동 사용 기능
    def use_pins(self):
        # 사용 방법 선택 다이얼로그
        selectbox = QMessageBox(self)
        selectbox.setIcon(QMessageBox.Question)
        selectbox.setWindowTitle("PIN 자동 사용")
        selectbox.setText("\n사용 방법을 선택하세요.\n")
        browser = QPushButton("브라우저")
        ingame = QPushButton("HAOPLAY")
        cancel = QPushButton("취소")
        selectbox.addButton(browser, QMessageBox.AcceptRole)
        selectbox.addButton(ingame, QMessageBox.AcceptRole)
        selectbox.addButton(cancel, QMessageBox.RejectRole)

        selectbox.exec()
        
        clicked_button = selectbox.clickedButton()

        if clicked_button == ingame:
            ok = QMessageBox.question(self, "인게임 결제", "인게임 자동 결제를 사용하시겠습니까?")
            if ok == QMessageBox.Yes:
                result = self.use_pins_auto()
                QMessageBox.information(self, "결과", result)
                self.update_table()
        elif clicked_button == browser:
            amount, ok = QInputDialog.getInt(self, "브라우저 PIN 자동 채우기", "사용할 금액 입력:")
            if ok and amount > 0:
                result = self.use_pins_browser(amount)
                QMessageBox.information(self, "결과", result)
                self.update_table()
        
    def use_pins_browser(self, amount):
        if amount > 250000:
            return "한번에 최대 250,000원까지만 사용할 수 있습니다."
        selected_pins = self.manager.find_pins_for_amount(amount)
        if not selected_pins:
            return "충분한 잔액이 없습니다."
        if len(selected_pins) == 0:
            return "사용할 수 있는 핀 조합이 없습니다."
        
        QMessageBox.information(self, "준비", f"{amount}원을 사용하기 위해 {len(selected_pins)}개의 PIN을 사용합니다.")
        if len(selected_pins) > 1:
            QMessageBox.information(self, "준비", f"핀 입력창을 {len(selected_pins)-1}개 추가해 주세요.")
        QMessageBox.information(self, "준비", "첫번째 핀 입력창의 첫번째 칸을 클릭하고 PIN이 입력될 준비를 하세요.\n3초 후 시작합니다.")
        time.sleep(3)
        total_used = 0
        new_log_entry = ""
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            pyautogui.write(pin.replace("-", ""))  # PIN 입력
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        self.log_pin_usage(new_log_entry)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()

        return f"PIN {len(selected_pins)}개 {amount}원 사용이 완료되었습니다."

    # PIN 자동 사용 기능
    def use_pins_auto(self):
        # 현재 클립보드 데이터 저장
        original_clipboard = pyperclip.paste()
        total_used = 0
        new_log_entry = ""
        try:
            # 1️⃣ HAOPLAY 창 핸들 찾기
            haoplay_hwnd = user32.FindWindowW(None, "HAOPLAY")
            if not haoplay_hwnd:
                # print("❌ HAOPLAY 창을 찾을 수 없습니다.")
                return "❌ HAOPLAY 창을 찾을 수 없습니다."

            # 2️⃣ "Chrome_WidgetWin_0" 컨트롤 핸들 찾기 (웹뷰 컨트롤)
            webview_hwnd = user32.FindWindowExW(haoplay_hwnd, 0, "Chrome_WidgetWin_0", None)
            if not webview_hwnd:
                # print("❌ 웹뷰 컨트롤을 찾을 수 없습니다.")
                return "❌ 웹뷰 컨트롤을 찾을 수 없습니다."

            # print(f"✅ 웹뷰 컨트롤 핸들 찾음: {webview_hwnd}")

            # 3️⃣ 창 활성화 (child_hWnd로 변경)
            user32.SetForegroundWindow(webview_hwnd)  # 웹뷰 컨트롤을 최상위로 활성화
            time.sleep(0.5)  # 안정성을 위해 대기
            
            pyautogui.hotkey('ctrl', 'shift', 'j')  # DevTools 열기
            time.sleep(1)
            pyautogui.hotkey('ctrl', '`') # Console 탭으로 이동
            time.sleep(0.2)

            amount = int(self.find_amount())
            product_name = self.find_Product()
            new_log_entry += f'{product_name} - {amount}원\n'

            if amount > 250000:
                return "한번에 최대 250,000원까지만 사용할 수 있습니다."

            selected_pins = self.manager.find_pins_for_amount(amount)
            if not selected_pins:
                return "충분한 잔액이 없습니다."
            if len(selected_pins) == 0:
                return "사용할 수 있는 핀 조합이 없습니다."

            # 목록에서 최대 5개의 핀번호를 가져옴
            pins_to_inject = [selected_pins[i][0] for i in range(min(5, len(selected_pins)))]

            # 4️⃣ 핀번호를 입력박스에 추가
            self.add_pin_input_box(len(pins_to_inject))
            time.sleep(0.2)

            # 5️⃣ 핀번호들 자바스크립트를 통해 입력
            self.inject_pin_codes(pins_to_inject)

            # 모두 동의
            self.click_all_agree()

            # 제출
            if config['SETTING']['auto_submit'] == 'True':
                self.submit()
            # self.submit()

        except Exception as e:
            return f"❌ 자동 입력에 실패했습니다.\n{e}"

        finally:
            # 클립보드 데이터 원래 값으로 복원
            pyperclip.copy(original_clipboard)
            # print("✅ 클립보드 복원 완료.")

        # 사용한 핀의 잔액을 갱신하고 사용한 핀을 삭제
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        self.log_pin_usage(new_log_entry)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()

        return f"{product_name}\nPIN {len(selected_pins)}개 {amount}원 사용이 완료되었습니다."
    
    # PIN 사용 로그를 파일에 기록하는 기능
    def log_pin_usage(self, new_log_entry):
        with open("pin_usage_log.txt", "w") as log_file:
            log_file.write(new_log_entry)

    def find_amount(self):
        javascript_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[2]/dd/strong', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);'''
        self.paste_javascript_code(javascript_code)
        time.sleep(0.2)
        amount = pyperclip.paste()
        amount = amount.replace(" ", "")
        amount = amount.replace(",", "")
        # print(amount)
        return amount
    
    def find_Product(self):
        javascript_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[1]/dd', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);
'''
        self.paste_javascript_code(javascript_code)
        time.sleep(0.2)
        name = pyperclip.paste()
        return name
    
    # 핀을 입력할 박스를 추가하는 기능
    def add_pin_input_box(self, num):
        if num < 1:
            return "사용되는 핀이 없습니다."

        # 5️⃣ 자바스크립트 코드 준비
        javascript_code = f'''
            while(document.querySelector("input[name='pyo_cnt']").value < {num})
                PinBoxInsert('pyo_cnt');
        '''
        self.paste_javascript_code(javascript_code)
    
    # javascript 코드를 붙여넣는 기능
    def inject_pin_codes(self, pins: list[str]):
        if pins is None or len(pins) == 0:
            return "사용되는 핀이 없습니다."

        arr = [item for pin in pins for item in pin.split("-")]
        arr_text = f"['{"', '".join(arr)}']"
        # 5️⃣ 자바스크립트 코드 준비
        javascript_code = '''
            let i = 0;
            arr = arr_text;
            document.querySelectorAll("#pinno").forEach(obj => {
                obj.querySelectorAll("input").forEach(input => {
                    input.value = arr[i++];
                })
            })
        '''.replace("arr_text", arr_text)
        self.paste_javascript_code(javascript_code)
    
    # javascript 코드를 붙여넣는 기능
    def paste_javascript_code(self, javascript_code):
        # 6️⃣ 클립보드에 자바스크립트 코드 복사 (pyperclip 사용)
        pyperclip.copy(javascript_code)
        # print(f"✅ 자바스크립트 코드 클립보드에 복사 완료.\n{pyperclip.paste()}")

        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)

        # 8️⃣ Enter 키 입력 (자바스크립트 실행)
        pyautogui.press('enter')
        time.sleep(0.1)

        # print("✅ 자바스크립트 실행 완료.")

    def click_all_agree(self):
        javascript_code = 'document.querySelector("#all-agree").click()'
        self.paste_javascript_code(javascript_code)


    def submit(self):
        javascript_code = 'goSubmit(document.form)'
        self.paste_javascript_code(javascript_code)


if __name__ == "__main__":
    config_read()
    app = QApplication(sys.argv)
    ex = PinManagerApp()
    ex.show()
    sys.exit(app.exec())
