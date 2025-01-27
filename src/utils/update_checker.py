"""
업데이트 확인 유틸리티
GitHub API를 사용하여 새 버전 확인
"""

# import json
import requests
from typing import Tuple, Optional
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
from ..config.config_manager import get_config
from ..__init__ import __version__

GITHUB_API_URL = "https://api.github.com/repos/TUVup/EggPinManager/releases/latest"
CURRENT_VERSION = __version__  # 현재 버전

def parse_version(version: str) -> Tuple[int, ...]:
    """
    버전 문자열을 튜플로 변환
    
    Args:
        version (str): 버전 문자열 (예: "1.0.0")
        
    Returns:
        Tuple[int, ...]: 버전 숫자 튜플
    """
    return tuple(map(int, version.replace('v', '').split('.')))

def check_for_updates(parent=None) -> Optional[str]:
    """
    GitHub에서 최신 버전 확인
    
    Args:
        parent: QWidget 부모 객체 (메시지 박스 표시용)
        
    Returns:
        Optional[str]: 새 버전이 있을 경우 버전 문자열, 없으면 None
    """
    config = get_config()

    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        response.raise_for_status()
        
        release_data = response.json()
        latest_version = release_data['tag_name']
        
        if parse_version(latest_version) > parse_version(CURRENT_VERSION):
            if parent:
                msg = QMessageBox(parent)
                msg.setWindowTitle("업데이트 알림")
                msg.setText(f"새로운 버전이 있습니다: {latest_version}")
                msg.setInformativeText("GitHub에서 새 버전을 다운로드하시겠습니까?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                
                if msg.exec() == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open(release_data['html_url'])
            
            return latest_version
        else:
            QMessageBox.information(parent, "업데이트 확인", "현제 최신 버전 입니다.") 
            return None
            
    except Exception as e:
        if parent:
            QMessageBox.warning(parent, "업데이트 확인 실패", f"업데이트 확인 중 오류 발생: {str(e)}")
    finally:
        # 마지막 업데이트 확인 시간 저장
        config.set_value('DEFAULT', 'last_update_check', datetime.now().isoformat())
    
    return None

def check_for_updates_auto(parent=None) -> Optional[str]:
    """
    GitHub에서 최신 버전 확인
    
    Args:
        parent: QWidget 부모 객체 (메시지 박스 표시용)
        
    Returns:
        Optional[str]: 새 버전이 있을 경우 버전 문자열, 없으면 None
    """
    config = get_config()
    
    # 마지막 업데이트 확인 시간 검사
    last_check = config.get_value('DEFAULT', 'last_update_check')
    if last_check:
        last_check_time = datetime.fromisoformat(last_check)
        if (datetime.now() - last_check_time).days < 1:
            return None

    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        response.raise_for_status()
        
        release_data = response.json()
        latest_version = release_data['tag_name']
        
        if parse_version(latest_version) > parse_version(CURRENT_VERSION):
            if parent:
                msg = QMessageBox(parent)
                msg.setWindowTitle("업데이트 알림")
                msg.setText(f"새로운 버전이 있습니다: {latest_version}")
                msg.setInformativeText("GitHub에서 새 버전을 다운로드하시겠습니까?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                
                if msg.exec() == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open(release_data['html_url'])
            
            return latest_version
            
    except Exception as e:
        if parent:
            QMessageBox.warning(parent, "업데이트 확인 실패", f"업데이트 확인 중 오류 발생: {str(e)}")
    finally:
        # 마지막 업데이트 확인 시간 저장
        config.set_value('DEFAULT', 'last_update_check', datetime.now().isoformat())
    
    return None