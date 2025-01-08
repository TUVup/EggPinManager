import json
import sys
import os
import time
import pyautogui
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout, QHeaderView
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
        if pin in self.pins:
            return f"PIN {pin}은(는) 이미 존재합니다."
        self.pins[pin] = balance
        self.save_pins()
        self.save_pins_to_txt()
        return f"PIN {pin} 추가 완료. 잔액: {balance}"

    def delete_pin(self, pin):
        if pin in self.pins:
            del self.pins[pin]
            self.save_pins()
            self.save_pins_to_txt()
            return f"PIN {pin} 삭제 완료."
        return f"PIN {pin}은(는) 존재하지 않습니다."

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

    # def use_pins(self, amount):
    #     selected_pins = self.find_pins_for_amount(amount)

    #     if not selected_pins:
    #         return "충분한 잔액이 없습니다."

    #     total_used = 0
    #     for pin, balance in selected_pins:
    #         if total_used >= amount:
    #             break
    #         QMessageBox.information(None, "준비", "브라우저 창을 선택하고 PIN이 입력될 준비를 하세요. 3초 후 시작합니다.")
    #         time.sleep(3)
    #         pyautogui.write(pin.replace("-", ""))  # PIN 입력
    #         remaining_balance = balance - (amount - total_used)
    #         if remaining_balance > 0:
    #             self.pins[pin] = remaining_balance
    #             total_used = amount
    #         else:
    #             del self.pins[pin]
    #             total_used += balance
    #             if total_used < amount:
    #                 QMessageBox.information(None, "준비", "'추가'를 누르고 PIN이 입력될 준비를 하세요.")

    #     self.save_pins()
    #     self.save_pins_to_txt()
    #     return "PIN 사용이 완료되었습니다."
    
    def pin_check(self, pin):
        for pins in self.pins.keys():
            if pins == pin:
                return 1
            else:
                return 0

class PinManagerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = PinManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("EggManager")
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
        pin, ok = QInputDialog.getText(self, "PIN 추가", "PIN 입력 (형식: 12345-12345-12345-12345):")
        if self.manager.pin_check(pin) == 1:
            QMessageBox.warning(self, "PIN오류", "중복된 PIN입니다.")
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
            cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if cancel == QMessageBox.Yes:
                result = self.manager.delete_pin(pin)
                QMessageBox.information(self, "결과", result)
                self.update_table()

    def use_pins(self):
        amount, ok = QInputDialog.getInt(self, "PIN 자동 사용", "사용할 금액 입력:")
        if ok and amount > 0:
            # result = self.manager.use_pins(amount)
            result = self.use_pins_calc(amount)
            QMessageBox.information(self, "결과", result)
            self.update_table()

    def use_pins_calc(self, amount):
        selected_pins = self.manager.find_pins_for_amount(amount)

        if not selected_pins:
            return "충분한 잔액이 없습니다."

        total_used = 0
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            QMessageBox.information(self, "준비", "브라우저 창을 선택하고 PIN이 입력될 준비를 하세요. 3초 후 시작합니다.")
            time.sleep(3)
            pyautogui.write(pin.replace("-", ""))  # PIN 입력
            remaining_balance = balance - (amount - total_used)
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance
                if total_used < amount:
                    QMessageBox.information(self, "준비", "'추가'를 누르고 PIN이 입력될 준비를 하세요.")

        self.manager.save_pins()
        self.manager.save_pins_to_txt()
        return "PIN 사용이 완료되었습니다."
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = PinManagerApp()
    ex.show()
    sys.exit(app.exec_())
