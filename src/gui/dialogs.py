"""
대화상자 관련 GUI 컴포넌트
설정 및 정보 대화상자 구현
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QTabWidget,
    QWidget,
    QGroupBox,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt
from ..config.config_manager import get_config
from src import __version__


class SettingsDialog(QDialog):
    """설정 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.setup_ui()

    def setup_ui(self):
        """UI 초기화"""
        self.setWindowTitle("설정")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # 탭 위젯 생성
        tab_widget = QTabWidget()

        # 일반 탭
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        # 자동 업데이트 확인
        update_check_group = QGroupBox("업데이트")
        update_layout = QVBoxLayout(update_check_group)
        self.auto_update_check = QCheckBox("시작 시 자동으로 업데이트 확인")
        self.auto_update_check.setChecked(
            self.config.get_value("DEFAULT", "auto_update_check", "True").lower()
            == "true"
        )
        update_layout.addWidget(self.auto_update_check)
        general_layout.addWidget(update_check_group)

        # 자동 결제 설정
        payments_group = QGroupBox("자동 결제")
        payments_layout = QVBoxLayout(payments_group)
        self.payments_check = QCheckBox("자동 결제 사용")
        self.payments_check.setChecked(
            self.config.get_value("DEFAULT", "payments", "True").lower() == "true"
        )
        payments_layout.addWidget(self.payments_check)
        general_layout.addWidget(payments_group)

        # 자동 백업 설정
        backup_group = QGroupBox("자동 백업")
        backup_layout = QVBoxLayout(backup_group)

        self.auto_backup_check = QCheckBox("자동 백업 사용")
        self.auto_backup_check.setChecked(
            self.config.get_value("DEFAULT", "auto_backup", "True").lower() == "true"
        )


        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("백업 간격:"))
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 1440)  # 1분 ~ 24시간
        self.backup_interval.setValue(
            int(self.config.get_value("DEFAULT", "backup_interval", "30"))
        )
        interval_layout.addWidget(self.backup_interval)
        interval_layout.addWidget(QLabel("분"))
        interval_layout.addStretch()

        backup_layout.addWidget(self.auto_backup_check)
        backup_layout.addLayout(interval_layout)
        general_layout.addWidget(backup_group)

        # 모양 탭
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)

        # 테마 설정
        theme_group = QGroupBox("테마")
        theme_layout = QVBoxLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["라이트", "다크"])
        current_theme = self.config.get_value("DEFAULT", "theme", "light")
        self.theme_combo.setCurrentText("다크" if current_theme == "dark" else "라이트")
        theme_layout.addWidget(self.theme_combo)
        appearance_layout.addWidget(theme_group)

        # 폰트 크기 설정
        font_group = QGroupBox("폰트")
        font_layout = QHBoxLayout(font_group)
        font_layout.addWidget(QLabel("크기:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(int(self.config.get_value("DEFAULT", "font_size", "9")))
        font_layout.addWidget(self.font_size)
        font_layout.addStretch()
        appearance_layout.addWidget(font_group)

        appearance_layout.addStretch()

        # 탭 추가
        tab_widget.addTab(general_tab, "일반")
        tab_widget.addTab(appearance_tab, "모양")

        layout.addWidget(tab_widget)

        # 확인/취소 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        """설정 저장"""
        # 일반 설정
        self.config.set_value(
            "DEFAULT", "auto_update_check", str(self.auto_update_check.isChecked())
        )
        self.config.set_value(
            "DEFAULT", "auto_backup", str(self.auto_backup_check.isChecked())
        )
        self.config.set_value(
            "DEFAULT", "backup_interval", str(self.backup_interval.value())
        )
        self.config.set_value(
            "DEFAULT", "payments", str(self.payments_check.isChecked())
        )

        # 모양 설정
        theme = "dark" if self.theme_combo.currentText() == "다크" else "light"
        self.config.set_value("DEFAULT", "theme", theme)
        self.config.set_value("DEFAULT", "font_size", str(self.font_size.value()))

        super().accept()


class AboutDialog(QDialog):
    """정보 대화상자"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """UI 구성"""
        self.setWindowTitle("프로그램 정보")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # 프로그램 정보
        title_label = QLabel("EggPinManager")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        version_label = QLabel(f"버전: {__version__}")
        version_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(
            "PIN 번호를 관리하고 자동으로 입력할 수 있는 프로그램입니다."
            "\n\n제작자: TUVup"
            "\n\n© 2024 All rights reserved."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)

        link_label = QLabel()
        link_label.setText("GitHub: <a href='https://github.com/TUVup/EggPinManager' style='color: orange;'>https://github.com/TUVup/EggPinManager</a>")
        link_label.setOpenExternalLinks(True)
        link_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        link_label.setAlignment(Qt.AlignCenter)

        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(link_label)
        layout.addStretch()
        layout.addWidget(close_button)

        self.setLayout(layout)
