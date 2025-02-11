"""
PIN Manager Application
메인 패키지 초기화 파일
"""

from .config.config_manager import get_config
from .models.pin_manager import PinManager
from .utils.logger import logger

__version__ = 'v1.0.7'
__author__ = 'TUVup'

# 주요 컴포넌트들을 패키지 레벨에서 직접 접근 가능하도록 설정
__all__ = [
    'get_config',
    'PinManager',
    'logger',
    '__version__',
    '__author__'
]