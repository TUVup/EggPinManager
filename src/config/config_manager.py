"""
설정 관리 모듈
애플리케이션의 설정을 관리하고 파일로 저장/로드하는 기능 제공
"""

import os
import configparser
from typing import Dict, Optional
from pathlib import Path


class ConfigManager:
    """설정 관리를 위한 클래스"""
    
    DEFAULT_CONFIG = {
        'DEFAULT': {
            'pin_file': 'pins.json',
            'txt_file': 'pins.txt',
            'log_file': 'pin_log.txt',
            'auto_backup': 'True',
            'backup_interval': '5',
            'theme': 'light',
            'font_size': '9',
            'window_width': '800',
            'window_height': '600',
            'last_update_check': '',
            'auto_update_check': 'True',
            'payments': 'False'
        }
    }

    def __init__(self, config_file: str = 'config.ini'):
        """
        ConfigManager 초기화
        
        Args:
            config_file (str): 설정 파일 경로
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self) -> None:
        """설정 파일 로드, 없으면 기본 설정으로 생성"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self._create_default_config()

    def _create_default_config(self) -> None:
        """기본 설정 파일 생성"""
        self.config.read_dict(self.DEFAULT_CONFIG)
        self.save_config()

    def save_config(self) -> None:
        """현재 설정을 파일에 저장"""
        with open(self.config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def get_value(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """
        설정값 조회
        
        Args:
            section (str): 설정 섹션
            key (str): 설정 키
            fallback (Optional[str]): 기본값
            
        Returns:
            str: 설정값
        """
        if not fallback:
            fallback = self.config[section][key]
        return self.config.get(section, key, fallback=fallback)

    def set_value(self, section: str, key: str, value: str) -> None:
        """
        설정값 변경
        
        Args:
            section (str): 설정 섹션
            key (str): 설정 키
            value (str): 설정값
        """
        if not self.config.has_section(section) and section != 'DEFAULT':
            self.config.add_section(section)
        self.config[section][key] = str(value)
        self.save_config()

    def get_all_settings(self) -> Dict[str, Dict[str, str]]:
        """
        모든 설정값 조회
        
        Returns:
            Dict[str, Dict[str, str]]: 전체 설정 딕셔너리
        """
        return {section: dict(self.config[section]) for section in self.config.sections()}

    def reset_to_default(self) -> None:
        """설정을 기본값으로 초기화"""
        self.config.clear()
        self._create_default_config()

    def ensure_paths(self) -> None:
        """필요한 디렉토리와 파일 생성"""
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)

        # 필요한 파일 경로 설정
        paths = ['pin_file', 'txt_file', 'log_file']
        for path_key in paths:
            current_path = self.get_value('DEFAULT', path_key)
            if not current_path.startswith('data/'):
                new_path = f"data/{current_path}"
                self.set_value('DEFAULT', path_key, new_path)

    @property
    def pin_file(self) -> str:
        """PIN 파일 경로"""
        return self.get_value('DEFAULT', 'pin_file')

    @property
    def txt_file(self) -> str:
        """텍스트 파일 경로"""
        return self.get_value('DEFAULT', 'txt_file')

    @property
    def log_file(self) -> str:
        """로그 파일 경로"""
        return self.get_value('DEFAULT', 'log_file')

    @property
    def auto_backup(self) -> bool:
        """자동 백업 설정"""
        return self.get_value('DEFAULT', 'auto_backup')

    @property
    def backup_interval(self) -> int:
        """백업 주기(분)"""
        return int(self.get_value('DEFAULT', 'backup_interval'))

    @property
    def theme(self) -> str:
        """테마 설정"""
        return self.get_value('DEFAULT', 'theme', 'light')

    @property
    def font_size(self) -> int:
        """폰트 크기"""
        return int(self.get_value('DEFAULT', 'font_size', '9'))

    @property
    def window_size(self) -> tuple:
        """윈도우 크기"""
        width = int(self.get_value('DEFAULT', 'window_width', '800'))
        height = int(self.get_value('DEFAULT', 'window_height', '600'))
        return (width, height)


# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()

def config_read() -> configparser.ConfigParser:
    """
    설정 파일 읽기
    
    Returns:
        configparser.ConfigParser: 설정 객체
    """
    config_manager.load_config()
    config_manager.ensure_paths()
    return config_manager.config

def config_write(section: str, key: str, value: str) -> None:
    """
    설정값 저장
    
    Args:
        section (str): 설정 섹션
        key (str): 설정 키
        value (str): 설정값
    """
    config_manager.set_value(section, key, value)

def get_config() -> ConfigManager:
    """
    설정 관리자 인스턴스 반환
    
    Returns:
        ConfigManager: 설정 관리자 인스턴스
    """
    return config_manager