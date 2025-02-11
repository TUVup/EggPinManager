"""
메인 윈도우 GUI 구현
애플리케이션의 주 인터페이스
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QStatusBar,
    QHeaderView,
    QInputDialog,
    QRadioButton,
    QFrame,
    QButtonGroup,
    QStyledItemDelegate
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
import time
import pyautogui
import pyperclip
from datetime import datetime
from ctypes import windll

from ..models.pin_manager import PinManager
from ..config.config_manager import get_config
from ..utils.logger import logger
from ..utils.update_checker import check_for_updates, check_for_updates_auto
from ..utils.backup_manager import BackupManager
from .dialogs import SettingsDialog, AboutDialog
from .styles import Styles

# Windows API 사용을 위한 설정
user32 = windll.user32

class NumberFormatDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        if isinstance(value, (int, float)):
            formatted_value = "{:,.0f}".format(value) if isinstance(value, float) else "{:,}".format(value)
            return formatted_value
        return super().displayText(value, locale)

class PinManagerApp(QMainWindow):
    """PIN 관리자 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.pin_manager = PinManager(self.config.config)
        self.backup_manager = BackupManager()
        
        # balance_label을 먼저 초기화
        self.balance_label = QLabel()
        
        self.init_ui()
        self.load_settings()
        self.setup_auto_backup()

        # 업데이트 체크
        if self.config.get_value("DEFAULT", "auto_update_check") == "True":
            QTimer.singleShot(1000, check_for_updates_auto)

        # status_bar에 balance_label 추가
        self.status_bar.addPermanentWidget(self.balance_label)
        self.update_total_balance()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("EggPinManager")
        self.setMinimumSize(800, 600)
        
        self.create_menu_bar()
        self.create_central_widget()
        self.create_status_bar()
        self.update_pin_list()

    def create_central_widget(self):
        """중앙 위젯 생성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        layout.addLayout(self.create_input_area())
        layout.addWidget(self.create_pin_table())

    def create_input_area(self):
        """PIN 입력 영역 생성"""
        input_layout = QHBoxLayout()
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("PIN 번호 입력 (예: 12345-67890-12345-67890)")
        
        self.balance_input = QLineEdit()
        self.balance_input.setPlaceholderText("잔액 입력")

        self.drawer_toggle_button = QPushButton("금액 선택", self)
        self.drawer_toggle_button.clicked.connect(self.toggle_drawer)

        #라디오 박스 프레임 생성
        self.drawer_widget = QFrame(self)
        self.drawer_widget.setFrameShape(QFrame.StyledPanel)
        drawer_layout = QVBoxLayout(self.drawer_widget)

        #라디오 버튼 설정
        self.credit_radio_btn1 = QRadioButton('1000')
        self.credit_radio_btn2 = QRadioButton('3000')
        self.credit_radio_btn3 = QRadioButton('5000')
        self.credit_radio_btn4 = QRadioButton('10000')
        self.credit_radio_btn5 = QRadioButton('30000')
        self.credit_radio_btn6 = QRadioButton('50000')
        self.radio_bg = QButtonGroup(self)
        self.radio_bg.addButton(self.credit_radio_btn1)
        self.radio_bg.addButton(self.credit_radio_btn2)
        self.radio_bg.addButton(self.credit_radio_btn3)
        self.radio_bg.addButton(self.credit_radio_btn4)
        self.radio_bg.addButton(self.credit_radio_btn5)
        self.radio_bg.addButton(self.credit_radio_btn6)
        self.radio_bg.buttonClicked.connect(self.select_credit)

        self.drawer_widget.setVisible(False)
        
        add_button = QPushButton("추가")
        add_button.clicked.connect(self.add_pin)
        
        auto_use_button = QPushButton("자동 사용")
        auto_use_button.clicked.connect(self._auto_use_pin)
        
        input_layout.addWidget(self.pin_input)
        input_layout.addWidget(self.balance_input)
        #금액 선택 라디오 박스
        input_layout.addWidget(self.drawer_toggle_button)
        drawer_layout.addWidget(self.credit_radio_btn1)
        drawer_layout.addWidget(self.credit_radio_btn2)
        drawer_layout.addWidget(self.credit_radio_btn3)
        drawer_layout.addWidget(self.credit_radio_btn4)
        drawer_layout.addWidget(self.credit_radio_btn5)
        drawer_layout.addWidget(self.credit_radio_btn6)
        input_layout.addWidget(self.drawer_widget)

        input_layout.addWidget(add_button)
        input_layout.addWidget(auto_use_button)
        
        return input_layout

    def create_pin_table(self):
        """PIN 목록 테이블 생성"""
        self.pin_table = QTableWidget()
        self.pin_table.setColumnCount(3)
        self.pin_table.setHorizontalHeaderLabels(["PIN", "잔액", "작업"])
        
        # 열 너비 설정
        header = self.pin_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # 정렬 기능 활성화
        # self.pin_table.setSortingEnabled(True)
        
        # 헤더 클릭 시 정렬 방향 변경 연결
        header.sectionClicked.connect(self._on_header_clicked)
        
        return self.pin_table

    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일")

        backup_action = QAction("백업 생성", self)
        backup_action.triggered.connect(self.create_backup)
        file_menu.addAction(backup_action)

        restore_action = QAction("백업 복원", self)
        restore_action.triggered.connect(self.restore_backup)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 설정 메뉴 (도구 메뉴를 설정으로 변경)
        settings_action = QAction("설정", self)
        settings_action.triggered.connect(self.show_settings)
        menubar.addAction(settings_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

        update_action = QAction("업데이트 확인", self)
        update_action.triggered.connect(self.check_updates)
        help_menu.addAction(update_action)

        about_action = QAction("정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def load_settings(self):
        """설정 로드 및 적용"""
        # 테마 적용
        theme = self.config.get_value("DEFAULT", "theme", "light")
        font_size = int(self.config.get_value("DEFAULT", "font_size", "9"))
        self.setStyleSheet(Styles.get_theme(theme, font_size))
        
        # 창 크기 복원
        width = int(self.config.get_value("DEFAULT", "window_width", "800"))
        height = int(self.config.get_value("DEFAULT", "window_height", "600"))
        self.resize(width, height)
    
    def toggle_drawer(self):
        # 현재 서랍의 상태를 토글
        is_visible = self.drawer_widget.isVisible()
        self.drawer_widget.setVisible(not is_visible)
        
        # 버튼 텍스트도 상태에 따라 변경
        # if not is_visible:
        #     self.drawer_toggle_button.setText("금액 선택(열기)")
        # else:
        #     self.drawer_toggle_button.setText("금액 선택(닫기)")
    
    def select_credit(self, button):
        """라디오 박스 금액 선택 적용"""
        tmp = button.text()
        self.balance_input.setText(tmp)

    def setup_auto_backup(self):
        """자동 백업 타이머 설정"""
        # 기존 타이머가 있으면 중지
        if hasattr(self, 'backup_timer') and self.backup_timer.isActive():
            self.backup_timer.stop()
    
        if self.config.auto_backup == "True":
            self.backup_timer = QTimer(self)
            self.backup_timer.timeout.connect(self.create_backup)
            interval = self.config.backup_interval * 60 * 1000  # 분 -> 밀리초
            self.backup_timer.start(interval)

    def update_total_balance(self):
        """전체 잔액 업데이트 및 표시"""
        total = self.pin_manager.get_total_balance()
        self.balance_label.setText(f"전체 잔액: {total:,}원")

    def update_pin_list(self):
        """PIN 목록 테이블 업데이트"""
        # 정렬 기능 임시 비활성화
        # self.pin_table.setSortingEnabled(False)
        
        self.pin_table.setRowCount(0)
        for pin, balance in self.pin_manager.list_pins():
            row = self.pin_table.rowCount()
            self.pin_table.insertRow(row)

            # PIN
            pin_item = QTableWidgetItem(pin)
            pin_item.setFlags(pin_item.flags() & ~Qt.ItemIsEditable)
            pin_item.setTextAlignment(Qt.AlignCenter)
            self.pin_table.setItem(row, 0, pin_item)

            # 잔액 (숫자 정렬을 위해 데이터 역할 설정)
            balance_item = QTableWidgetItem()
            balance_item.setData(Qt.DisplayRole, balance)  # 정렬을 위한 데이터
            balance_item.setData(Qt.EditRole, balance)
            balance_item.setData(Qt.TextAlignmentRole, Qt.AlignCenter)
            balance_item.setFlags(balance_item.flags() & ~Qt.ItemIsEditable)
            # balance_item.setText(f"{balance:,}")  # 표시용 텍스트
            balance_item.setText(f"{balance}")
            self.pin_table.setItem(row, 1, balance_item)

            # 작업 버튼
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setAlignment(Qt.AlignCenter)

            edit_button = QPushButton("수정")
            edit_button.clicked.connect(lambda _, p=pin, b=balance: self.edit_balance(p, b))

            delete_button = QPushButton("삭제")
            delete_button.clicked.connect(lambda _, p=pin: self.delete_pin(p))

            button_layout.addWidget(edit_button)
            button_layout.addWidget(delete_button)

            self.pin_table.setCellWidget(row, 2, button_widget)

        # 정렬 기능 다시 활성화
        # self.pin_table.setSortingEnabled(True)

        # 보기 편하게 잔액에 ,추가
        delegate = NumberFormatDelegate(self.pin_table)
        self.pin_table.setItemDelegateForColumn(1, delegate)
        
        # 전체 잔액 업데이트
        self.update_total_balance()

    def edit_balance(self, pin: str, current_balance: int):
        """잔액 수정"""
        new_balance, ok = QInputDialog.getInt(
            self, 
            "잔액 수정", 
            f"PIN: {pin}\n새로운 잔액을 입력하세요:", 
            current_balance, 
            1, 
            50000
        )
        
        if ok:
            self.pin_manager.update_pin_balance(pin, new_balance)
            self.update_pin_list()
            self.status_bar.showMessage(f"잔액이 수정되었습니다: {new_balance:,}원", 3000)

    def add_pin(self):
        """PIN 추가"""
        pin = self.pin_input.text().strip()
        balance = self.balance_input.text().strip()

        if not pin or not balance:
            QMessageBox.warning(self, "입력 오류", "PIN과 잔액을 모두 입력해주세요.")
            return

        try:
            balance = int(balance)
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "잔액은 숫자로 입력해주세요.")
            return

        if not self.pin_manager.is_valid_pin_format(pin):
            formatted_pin = self.pin_manager.format_pin(pin)
            if self.pin_manager.is_valid_pin_format(formatted_pin):
                pin = formatted_pin
            else:
                QMessageBox.warning(
                    self,
                    "입력 오류",
                    "올바른 PIN 형식이 아닙니다.\n예: 12345-67890-12345-67890",
                )
                return

        if self.pin_manager.pin_check(pin):
            QMessageBox.warning(self, "중복 오류", "이미 존재하는 PIN입니다.")
            return

        self.pin_manager.add_pin(pin, balance)
        self.update_pin_list()
        self.pin_input.clear()
        self.balance_input.clear()

    def delete_pin(self, pin: str):
        """PIN 삭제"""
        reply = QMessageBox.question(
            self,
            "삭제 확인",
            f"PIN {pin}을(를) 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.pin_manager.delete_pin(pin)
            self.update_pin_list()

    def create_backup(self):
        """백업 생성"""
        try:
            backup_name = self.backup_manager.create_backup()
            self.status_bar.showMessage(f"백업 생성 완료: {backup_name}", 3000)
            logger.info(f"백업 생성: {backup_name}")
        except Exception as e:
            QMessageBox.warning(self, "백업 오류", f"백업 생성 중 오류 발생: {e}")
            logger.error(f"백업 생성 실패: {e}")

    def restore_backup(self):
        """백업 복원"""
        backups = self.backup_manager.list_backups()
        if not backups:
            QMessageBox.information(self, "백업 복원", "사용 가능한 백업이 없습니다.")
            return

        # 백업 선택 대화상자
        backup_name, ok = QInputDialog.getItem(
            self,
            "백업 복원",
            "복원할 백업을 선택하세요:",
            backups,
            0,  # 기본값으로 가장 최근 백업 선택
            False  # 수정 불가능
        )
        
        if ok and backup_name:
            try:
                self.backup_manager.restore_backup(backup_name)
                # PIN 매니저 데이터 리로드
                self.pin_manager = PinManager(self.config.config)
                self.update_pin_list()
                self.status_bar.showMessage(f"백업 복원 완료: {backup_name}", 3000)
                logger.info(f"백업 복원: {backup_name}")
            except Exception as e:
                QMessageBox.warning(self, "복원 오류", f"백업 복원 중 오류 발생: {e}")
                logger.error(f"백업 복원 실패: {e}")

    def show_settings(self):
        """설정 대화상자 표시"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.load_settings()
            self.setup_auto_backup()

    def show_about(self):
        """정보 대화상자 표시"""
        dialog = AboutDialog(self)
        dialog.exec()

    def check_updates(self):
        """업데이트 확인"""
        check_for_updates(parent=self)

    def closeEvent(self, event):
        """프로그램 종료 시 처리"""
        # 창 크기 저장
        self.config.set_value("DEFAULT", "window_width", str(self.width()))
        self.config.set_value("DEFAULT", "window_height", str(self.height()))

        # 자동 백업
        if self.config.auto_backup:
            try:
                self.create_backup()
            except Exception as e:
                logger.error(f"종료 시 자동 백업 실패: {e}")

        event.accept()
    
    def _auto_use_pin(self):
        """PIN 자동 사용"""
        # 사용 모드 선택
        mode, ok = QInputDialog.getItem(
            self,
            "자동 사용 모드 선택",
            "사용할 모드를 선택하세요:",
            ["HAOPLAY", "웹 브라우저"],
            0,  # 기본값으로 HAOPLAY 선택
            False  # 수정 불가능
        )
        
        if not ok:
            return
            
        if mode == "HAOPLAY":
            self._auto_use_pin_haoplay()
        else:
            self._auto_use_pin_browser()

    def _auto_use_pin_haoplay(self):
        """PIN 자동 사용"""
        try:
            # 현재 클립보드 데이터 저장
            original_clipboard = pyperclip.paste()
            
            try:
                # HAOPLAY 창 찾기
                haoplay_hwnd = user32.FindWindowW(None, "HAOPLAY")
                if not haoplay_hwnd:
                    raise Exception("HAOPLAY 창을 찾을 수 없습니다.")

                # 웹뷰 컨트롤 찾기
                webview_hwnd = user32.FindWindowExW(haoplay_hwnd, 0, "Chrome_WidgetWin_0", None)
                if not webview_hwnd:
                    raise Exception("웹뷰 컨트롤을 찾을 수 없습니다.")

                # 창 활성화
                user32.SetForegroundWindow(webview_hwnd)
                time.sleep(0.5)

                # DevTools 열기 및 Console 탭으로 이동
                pyautogui.hotkey('ctrl', 'shift', 'j')
                time.sleep(1)
                pyautogui.hotkey('ctrl', '`')
                time.sleep(0.2)

                # 금액과 상품명 찾기
                amount = self._find_amount()
                product_name = self._find_product()
                
                if not amount or not product_name:
                    raise Exception("금액 또는 상품명을 찾을 수 없습니다.")

                amount = int(amount)
                if amount > 250000:
                    raise Exception("한번에 최대 250,000원까지만 사용할 수 있습니다.")

                # PIN 선택
                selected_pins = self.pin_manager.find_pins_for_amount(amount)
                if not selected_pins:
                    raise Exception("충분한 잔액이 없습니다.")

                # 최대 5개의 PIN 선택
                pins_to_inject = [pin[0] for pin in selected_pins[:5]]

                # PIN 입력 박스 추가
                self._add_pin_input_box(len(pins_to_inject))
                time.sleep(0.2)

                # PIN 입력
                self._inject_pin_codes(pins_to_inject)

                # 동의 체크 및 제출
                self._click_all_agree()
                if self.config.get_value("DEFAULT", "payments") == "True":
                    self._submit()

                # PIN 사용 로그 기록
                self._log_pin_usage(product_name, amount, selected_pins)

                self.status_bar.showMessage(f"{product_name} - PIN {len(selected_pins)}개 {amount}원 사용 완료", 10000)

            finally:
                # 클립보드 복원
                pyperclip.copy(original_clipboard)

        except Exception as e:
            QMessageBox.warning(self, "자동 사용 오류", str(e))
            logger.error(f"PIN 자동 사용 오류: {e}")

    def _auto_use_pin_browser(self):
        """웹 브라우저에서 PIN 자동 사용"""
        try:
            # 금액 입력 받기
            amount, ok = QInputDialog.getInt(
                self,
                "금액 입력",
                "사용할 금액을 입력하세요:",
                value=1000,  # 기본값
                minValue=1,  # 최소값
                maxValue=250000  # 최대값
            )
            
            if not ok:
                return

            if amount > 250000:
                QMessageBox.warning(self, "입력 오류", "한번에 최대 250,000원까지만 사용할 수 있습니다.")
                return

            # PIN 선택
            selected_pins = self.pin_manager.find_pins_for_amount(amount)
            if not selected_pins:
                QMessageBox.warning(self, "오류", "충분한 잔액이 없습니다.")
                return
            if len(selected_pins) == 0:
                QMessageBox.warning(self, "오류", "사용할 수 있는 핀 조합이 없습니다.")
                return

            # 사용자에게 안내
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
                    self.pin_manager.pins[pin] = remaining_balance
                    total_used = amount
                else:
                    del self.pin_manager.pins[pin]
                    total_used += balance

            # 로그 기록
            with open("pin_usage_log.txt", "a", encoding='utf-8') as f:
                f.write(new_log_entry)

            # PIN 데이터 저장
            self.pin_manager.save_pins()
            self.pin_manager.save_pins_to_txt()
            
            # 테이블 업데이트
            self.update_pin_list()
            
            self.status_bar.showMessage(f"PIN {len(selected_pins)}개 {amount}원 사용이 완료되었습니다.", 10000)

        except Exception as e:
            QMessageBox.warning(self, "자동 사용 오류", str(e))
            logger.error(f"PIN 자동 사용 오류: {e}")

    def _find_amount(self):
        """결제 금액 찾기"""
        js_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[2]/dd/strong', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);'''
        self._paste_javascript_code(js_code)
        time.sleep(0.2)
        amount = pyperclip.paste()
        return amount.replace(" ", "").replace(",", "")

    def _find_product(self):
        """상품명 찾기"""
        js_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[1]/dd', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);'''
        self._paste_javascript_code(js_code)
        time.sleep(0.2)
        return pyperclip.paste()

    def _add_pin_input_box(self, num):
        """PIN 입력 박스 추가"""
        if num < 1:
            return
        js_code = f'''
            while(document.querySelector("input[name='pyo_cnt']").value < {num})
                PinBoxInsert('pyo_cnt');
        '''
        self._paste_javascript_code(js_code)

    def _inject_pin_codes(self, pins):
        """PIN 코드 입력"""
        if not pins:
            return
        arr = [item for pin in pins for item in pin.split("-")]
        arr_text = f"['{"', '".join(arr)}']"
        js_code = f'''
            let i = 0;
            arr = {arr_text};
            document.querySelectorAll("#pinno").forEach(obj => {{
                obj.querySelectorAll("input").forEach(input => {{
                    input.value = arr[i++];
                }})
            }})
        '''
        self._paste_javascript_code(js_code)

    def _paste_javascript_code(self, js_code):
        """자바스크립트 코드 실행"""
        pyperclip.copy(js_code)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(0.1)

    def _click_all_agree(self):
        """모두 동의 체크"""
        js_code = 'document.querySelector("#all-agree").click()'
        self._paste_javascript_code(js_code)

    def _submit(self):
        """폼 제출"""
        js_code = 'goSubmit(document.form)'
        self._paste_javascript_code(js_code)

    def _log_pin_usage(self, product_name, amount, selected_pins):
        """PIN 사용 로그 기록"""
        log_entry = f'{product_name} - {amount}원\n'
        logger.info(log_entry)
        total_used = 0

        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            
            log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            
            if remaining_balance > 0:
                self.pin_manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.pin_manager.pins[pin]
                total_used += balance

        with open("pin_usage_log.txt", "w", encoding='utf-8') as log_file:
            log_file.write(log_entry)

        self.pin_manager.save_pins()
        self.pin_manager.save_pins_to_txt()
        self.update_pin_list()

    def _on_header_clicked(self, logical_index):
        """헤더 클릭 시 정렬 처리"""
        if logical_index == 2 or logical_index == 0:  # '작업' 열은 정렬하지 않음
            return
            
        # 현재 정렬 상태 확인
        order = self.pin_table.horizontalHeader().sortIndicatorOrder()
        print(order)
        
        # 정렬 실행
        self.pin_table.sortItems(logical_index, order)
