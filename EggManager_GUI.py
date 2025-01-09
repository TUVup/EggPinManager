import json
import sys
import os
import re
import time
from datetime import datetime
import pyautogui
# from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QHeaderView, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class PinManager:
    def __init__(self, filename="pins.json", txt_filename="pins.txt"):
        self.filename = filename
        self.pins = self.load_pins()
        self.txt_filename = txt_filename

    def load_pins(self):
        try:
            with open(self.filename, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_pins(self):
        with open(self.filename, "w") as file:
            json.dump(self.pins, file, indent=4)
    
    def save_pins_to_txt(self):
        with open(self.txt_filename, "w") as file:
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                file.write(f"{idx}. {pin}: {balance}\n")

    def add_pin(self, pin, balance):
        self.pins[pin] = balance
        self.save_pins()
        self.save_pins_to_txt()
        return f"PIN {pin} 추가 완료. 잔액: {balance}"
    
    def format_pin(self, pin):
        if len(pin) == 20 and pin.isdigit():
            return f"{pin[:5]}-{pin[5:10]}-{pin[10:15]}-{pin[15:]}"
        return pin

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

        for pin, balance in sorted_pins:
            if total_selected >= amount:
                break
            selected_pins.append((pin, balance))
            total_selected += balance

        if total_selected >= amount:
            return selected_pins
        return []
    
    def pin_check(self, pin):
        pin = self.format_pin(pin)
        for pins in self.pins.keys():
            if pins == pin:
                return 1
        return 0

class PinManagerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = PinManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("EggManager 1.0.1")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setGeometry(300, 300, 600, 400)
        ico = resource_path('eggui.ico')
        self.setWindowIcon(QIcon(ico))
        layout = QVBoxLayout()

        # PIN 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["PIN 번호", "잔액"])
        #self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # 버튼 배치
        button_layout = QHBoxLayout()
        btn_add = QPushButton("PIN 추가", self)
        btn_add.clicked.connect(self.add_pin)
        button_layout.addWidget(btn_add)

        btn_delete = QPushButton("PIN 삭제", self)
        btn_delete.clicked.connect(self.delete_pin)
        button_layout.addWidget(btn_delete)

        btn_use = QPushButton("PIN 자동 사용", self)
        btn_use.clicked.connect(self.use_pins)
        button_layout.addWidget(btn_use)

        btn_quit = QPushButton("종료", self)
        btn_quit.clicked.connect(self.close)
        button_layout.addWidget(btn_quit)

        layout.addLayout(button_layout)

        self.sum = QLabel(f"잔액 : {self.manager.get_total_balance()}", self)
        layout.addWidget(self.sum)

        self.setLayout(layout)

        self.update_table()

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

        context_menu.exec_(self.mapToGlobal(event.pos()))

    def delete_selected_pin(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if cancel == QMessageBox.Yes:
                pin = selected_items[0].text()
                self.manager.delete_pin(pin)
                self.update_table()
    
    def edit_selected_pin_balance(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            pin = selected_items[0].text()
            new_balance, ok = QInputDialog.getInt(self, "잔액 수정", "새 잔액 입력:", min=0)
            if not ok:
                QMessageBox.warning(self, "취소", "잔액 수정이 취소되었습니다.")
                return
            if new_balance <= 0:
                QMessageBox.warning(self, "오류", "잔액은 0보다 커야 합니다.")
                return
            if ok:
                self.manager.update_pin_balance(pin, new_balance)
                QMessageBox.information(self, "성공", "잔액 수정이 완료되었습니다.")
                self.update_table()

    def update_table(self):
        self.sum.setText(f"잔액 : {self.manager.get_total_balance()}")
        pins = self.manager.list_pins()
        self.table.setRowCount(len(pins))
        for row, (pin, balance) in enumerate(pins):
            self.table.setItem(row, 0, QTableWidgetItem(pin))
            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(row, 1, QTableWidgetItem(str(balance)))
            self.table.item(row, 1).setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

    def add_pin(self):
        pin, ok = QInputDialog.getText(self, "PIN 추가", "PIN 입력 (핀 전체 또는 숫자만 입력):")
        pin = self.manager.format_pin(pin)
        if self.manager.pin_check(pin) == 1:
            QMessageBox.warning(self, "PIN오류", "중복된 PIN입니다.")
        elif not self.manager.is_valid_pin_format(pin) and ok:
            QMessageBox.warning(self, "오류", "올바른 PIN 형식이 아닙니다.")
        elif ok and pin:
            balance, ok = QInputDialog.getInt(self, "PIN 추가", "잔액 입력:")
            if ok and balance > 0:
                result = self.manager.add_pin(pin, balance)
                QMessageBox.information(self, "결과", result)
                self.update_table()
            elif balance <= 0:
                QMessageBox.warning(self, "금액 오류", "0보다 작은 금액은 입력할 수 없습니다.")
            elif not balance:
                QMessageBox.warning(self, "금액 오류", "금액은 반드시 입력해야 합니다.")

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

    def use_pins(self):
        amount, ok = QInputDialog.getInt(self, "PIN 자동 사용", "사용할 금액 입력:")
        if ok and amount > 0:
            result = self.use_pins_auto(amount)
            QMessageBox.information(self, "결과", result)
            self.update_table()

    def use_pins_auto(self, amount):
        if amount > 250000:
            return "한번에 최대 250,000원까지만 사용할 수 있습니다."
        selected_pins = self.manager.find_pins_for_amount(amount)
        if not selected_pins:
            return "충분한 잔액이 없습니다."
        if len(selected_pins) > 5:
            return f"{len(selected_pins)}개의 핀이 사용됩니다.\n핀은 최대 5개만 사용할 수 있습니다."
        
        QMessageBox.information(self, "준비", f"{amount}원을 사용하기 위해 {len(selected_pins)}개의 PIN을 사용합니다.")
        if len(selected_pins) > 1:
            QMessageBox.information(self, "준비", f"핀 입력창을 {len(selected_pins)-1}개 추가해 주세요.")
        QMessageBox.information(self, "준비", "첫번째 핀 입력창의 첫번째 칸을 클릭하고 PIN이 입력될 준비를 하세요.\n3초 후 시작합니다.")
        time.sleep(3)
        total_used = 0
        new_log_entry = ""
        pins_to_delete = []
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
                # del self.manager.pins[pin]
                pins_to_delete.append(pin)
                self.manager.pins[pin] = remaining_balance
                total_used += balance

        self.log_pin_usage(new_log_entry)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()

        if pins_to_delete:
            cancel = QMessageBox.warning(self, "삭제 확인", "잔액이 0인 PIN을 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if cancel == QMessageBox.Yes:
                for pin in pins_to_delete:
                    del self.manager.pins[pin]
                self.manager.save_pins()
                self.manager.save_pins_to_txt()

        return "PIN 사용이 완료되었습니다."
    
    def log_pin_usage(self, new_log_entry):
        with open("pin_usage_log.txt", "w") as log_file:
            log_file.write(new_log_entry)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = PinManagerApp()
    ex.show()
    sys.exit(app.exec_())
