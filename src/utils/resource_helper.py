"""
리소스 관리 유틸리티
애플리케이션에서 사용하는 리소스 파일의 경로를 관리
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """
    리소스 파일의 절대 경로를 반환
    PyInstaller로 패키징된 경우에도 정상 작동
    
    Args:
        relative_path (str): 리소스의 상대 경로
        
    Returns:
        str: 리소스의 절대 경로
    """
    try:
        # PyInstaller가 생성한 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 일반적인 실행 환경
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def ensure_directory(path: str) -> None:
    """
    디렉토리가 존재하지 않으면 생성
    
    Args:
        path (str): 생성할 디렉토리 경로
    """
    Path(path).mkdir(parents=True, exist_ok=True)