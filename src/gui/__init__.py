"""
GUI 모듈
사용자 인터페이스 관련 클래스들을 제공하는 패키지

Classes:
    PinManagerApp: 메인 애플리케이션 윈도우
    SettingsDialog: 설정 관리 대화상자
    AboutDialog: 프로그램 정보 대화상자
    AutoInputHandler: PIN 자동 입력 처리기
    Styles: UI 테마 및 스타일 관리
"""

from .main_window import PinManagerApp
from .dialogs import (
    SettingsDialog,
    AboutDialog
)
# from .auto_input import AutoInputHandler
from .styles import Styles

# 외부에서 접근 가능한 클래스 목록
__all__ = [
    'PinManagerApp',
    'SettingsDialog',
    'AboutDialog',
    # 'AutoInputHandler',
    'Styles'
]

# GUI 기본 설정
GUI_DEFAULTS = {
    'WINDOW_SIZE': (800, 600),
    'FONT_SIZE': 9,
    'THEME': 'light',
    'MIN_WINDOW_SIZE': (600, 400),
    'SPACING': 10,
    'MARGIN': 10
}

# 테이블 컬럼 설정
TABLE_COLUMNS = {
    'PIN': 0,
    'BALANCE': 1,
    'ACTIONS': 2
}

# 메시지 표시 시간 (밀리초)
MESSAGE_DURATION = 3000