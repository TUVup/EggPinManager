"""
PIN Manager Application
메인 실행 파일
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src import __version__
from src.gui import PinManagerApp
from src.config.config_manager import get_config
from src.utils.resource_helper import get_resource_path
from src.utils.logger import logger

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def setup_environment():
    """
    애플리케이션 환경 설정
    필요한 디렉토리 생성 및 기본 설정 확인
    """
    # 필요한 디렉토리 생성
    directories = ['data']
    for directory in directories:
        path = Path(directory)
        path.mkdir(exist_ok=True)

    # 설정 초기화
    config = get_config()
    config.ensure_paths()

    return config


def main():
    """메인 애플리케이션 실행"""
    try:
        # 환경 설정
        setup_environment()
        
        # 애플리케이션 초기화
        app = QApplication(sys.argv)
        app.setApplicationName("EggManager")
        app.setApplicationVersion(__version__)
        
        # 아이콘 설정
        icon_path = get_resource_path("resources/eggui.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            icon_path = resource_path('eggui.ico')
            app.setWindowIcon(QIcon(icon_path))
        
        # 메인 윈도우 생성
        window = PinManagerApp()
        window.show()
        
        # 시작 로그
        logger.info(f"애플리케이션 시작 (버전: {__version__})")
        
        # 이벤트 루프 시작
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()