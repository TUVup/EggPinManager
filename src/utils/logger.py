"""
로깅 유틸리티
애플리케이션 로그 관리
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

class Logger:
    """로깅 관리 클래스"""
    
    _instance: Optional['Logger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self) -> None:
        """로거 초기화"""
        self.logger = logging.getLogger('PinManager')
        self.logger.setLevel(logging.INFO)

        # 로그 디렉토리 생성
        log_dir = Path('data/logs')
        if not log_dir.exists():
            data_dir = Path('data')
            data_dir.mkdir(exist_ok=True)
        log_dir.mkdir(exist_ok=True)

        # 파일 핸들러 설정
        log_file = log_dir / f"pin_manager_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def info(self, message: str) -> None:
        """정보 로그 기록"""
        self.logger.info(message)

    def error(self, message: str) -> None:
        """에러 로그 기록"""
        self.logger.error(message)

    def warning(self, message: str) -> None:
        """경고 로그 기록"""
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        """디버그 로그 기록"""
        self.logger.debug(message)

# 전역 로거 인스턴스
logger = Logger()