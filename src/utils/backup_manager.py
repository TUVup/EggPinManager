"""
백업 관리 유틸리티
파일 백업 및 복원 기능 제공
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
import json

from ..utils.logger import logger

class BackupManager:
    """파일 백업 관리 클래스"""
    
    def __init__(self, data_dir: str = 'data', backup_dir: str = 'backups'):
        """
        BackupManager 초기화
        
        Args:
            data_dir (str): 데이터 디렉토리 경로
            backup_dir (str): 백업 디렉토리 경로
        """
        self.data_dir = Path(os.path.abspath(data_dir))
        self.backup_dir = Path(os.path.abspath(backup_dir))
        self.pins_file = self.data_dir / 'pins.json'
        
        # 디렉토리가 없으면 생성
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)

    def create_backup(self) -> str:
        """
        현재 pins.json 파일의 백업 생성
        
        Returns:
            str: 생성된 백업 파일 이름
        """
        try:
            if not self.pins_file.exists():
                raise FileNotFoundError("pins.json 파일을 찾을 수 없습니다.")

            # 백업 파일명 생성 (YY/MM/DD_HH:MM.json)
            backup_name = datetime.now().strftime('%y%m%d_%H%M%S.json')
            backup_path = self.backup_dir / backup_name
            
            # pins.json 파일 복사
            shutil.copy(self.pins_file, backup_path)
            logger.info(f"백업 생성 완료: {backup_name}")

            self.cleanup_old_backups()
            
            return backup_name

        except Exception as e:
            logger.error(f"백업 생성 실패: {str(e)}")
            raise

    def list_backups(self) -> List[str]:
        """
        사용 가능한 백업 파일 목록 반환
        
        Returns:
            List[str]: 백업 파일명 리스트 (최신순 정렬)
        """
        backups = []
        if self.backup_dir.exists():
            backups = [f.name for f in self.backup_dir.glob('**/*.json')]
            backups.sort(reverse=True)  # 최신 백업이 먼저 오도록 정렬
        return backups

    def get_backup_path(self, backup_name: str) -> Path:
        """
        백업 파일의 전체 경로 반환
        
        Args:
            backup_name (str): 백업 파일명
            
        Returns:
            Path: 백업 파일의 전체 경로
        """
        return self.backup_dir / backup_name

    def restore_backup(self, backup_name: str) -> bool:
        """
        백업 파일에서 pins.json 복원
        
        Args:
            backup_name (str): 복원할 백업 파일명
            
        Returns:
            bool: 복원 성공 여부
        """
        backup_path = self.backup_dir / backup_name
        
        try:
            # 백업 파일 존재 확인
            if not backup_path.exists():
                raise FileNotFoundError(f"백업 파일을 찾을 수 없습니다: {backup_name}")

            # 백업 파일 데이터 검증
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                # pins.json 파일 형식 검증 - pins 키가 있거나 빈 딕셔너리여야 함
                if not isinstance(backup_data, dict):
                    raise ValueError("잘못된 백업 파일 형식입니다: JSON 객체가 아닙니다.")

            # 현재 pins.json 임시 백업
            temp_backup = self.pins_file.with_suffix('.temp')
            if self.pins_file.exists():
                shutil.copy2(self.pins_file, temp_backup)

            try:
                # 백업 데이터로 pins.json 덮어쓰기
                with open(self.pins_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)
                
                # 임시 백업 파일 삭제
                if temp_backup.exists():
                    temp_backup.unlink()
                
                logger.info(f"백업 복원 완료: {backup_name}")
                return True

            except Exception as e:
                # 오류 발생 시 임시 백업에서 복구
                if temp_backup.exists():
                    shutil.copy2(temp_backup, self.pins_file)
                    temp_backup.unlink()
                logger.error(f"백업 복원 중 오류 발생: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"백업 복원 실패: {str(e)}")
            raise

    def cleanup_old_backups(self, keep_count: int = 10):
        """
        오래된 백업 파일 정리
        
        Args:
            keep_count (int): 유지할 최신 백업 수
        """
        try:
            backups = self.list_backups()
            if len(backups) > keep_count:
                for old_backup in backups[keep_count:]:
                    backup_path = self.backup_dir / old_backup
                    backup_path.unlink()
                    logger.info(f"오래된 백업 삭제: {old_backup}")
        except Exception as e:
            logger.error(f"백업 정리 중 오류 발생: {str(e)}")