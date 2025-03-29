import json
import sys
import os
import re
import time
import ctypes, pyperclip
from itertools import combinations
from datetime import datetime
import pyautogui
import webbrowser
import requests
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import configparser as cp
import pywinauto
from pywinauto import Application
from win32api import GetSystemMetrics
import win32con
import win32gui
import threading
import urllib.request
import zipfile
import shutil
import subprocess
import tempfile

current_version = "1.2.0"
config = cp.ConfigParser()

# Windows API 함수 로드
user32 = ctypes.windll.user32

def config_read():
    # 기본 설정값 정의
    default_settings = {
        'DEFAULT': {
            'pin_file': 'pins.json',
            'txt_file': 'pins.txt',
            'log_file': 'pin_usage_log.txt'
        },
        'SETTING': {
            'auto_update': 'True',
            'auto_submit': 'False',
            'theme': 'Light',
            'size_adjust': 'True'
        },
        'UPDATE': {
            'last_check': '0',  # 마지막 업데이트 확인 시간 (UNIX 타임스탬프)
            'check_interval': '86400',  # 업데이트 확인 간격 (초 단위, 기본 1일)
            'skip_version': '',  # 건너뛸 버전
        }
    }
    
    # 설정 파일 읽기 시도
    config_file_exists = config.read('config.ini')
    config_changed = False
    
    if not config_file_exists:
        # 설정 파일이 없는 경우 기본값으로 새로 생성
        for section, options in default_settings.items():
            if section not in config:
                config[section] = {}
            for option, value in options.items():
                config[section][option] = value
        config_changed = True
    else:
        # 설정 파일이 존재하는 경우, 필요한 항목이 누락되었는지 확인하고 추가
        for section, options in default_settings.items():
            if section not in config:
                config[section] = {}
                config_changed = True
            
            for option, value in options.items():
                if option not in config[section]:
                    config[section][option] = value
                    config_changed = True
    
    # 변경된 경우 설정 파일 저장
    if config_changed:
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    
    # resource 폴더가 없으면 생성
    os.makedirs("resource", exist_ok=True)
    
    return config

class AutoUpdater:
    def __init__(self, current_version, parent=None):
        self.current_version = f"v{current_version}"
        self.parent = parent
        self.github_api_url = "https://api.github.com/repos/TUVup/EggPinManager/releases/latest"
        self.github_download_url = "https://github.com/TUVup/EggPinManager/releases/latest/download/EggManager.zip"
        self.update_in_progress = False
        self.temp_dir = None
        self.update_thread = None
        self.cancel_requested = False  # 취소 요청 플래그 추가
        self.download_thread = None  # 다운로드 스레드 참조 추가
        self.update_completed = False  # 업데이트 완료 플래그 추가
    
    def check_for_updates_async(self, silent=False):
        """백그라운드 스레드에서 업데이트 확인"""
        if self.update_in_progress:
            return
            
        self.cancel_requested = False  # 취소 플래그 초기화
        self.update_thread = threading.Thread(
            target=self._check_and_update, 
            args=(silent,),
            daemon=True
        )
        self.update_thread.start()
    
    def _check_and_update(self, silent=False):
        """업데이트 확인 및 설치 프로세스"""
        self.update_in_progress = True
        try:
            # 최신 버전 정보 가져오기
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            
            latest_release = response.json()
            latest_version = latest_release["tag_name"]
            release_notes = latest_release.get("body", "업데이트 내용이 제공되지 않았습니다.")

            skip_version = config['UPDATE'].get('skip_version', '')

            # 건너뛸 버전과 동일한 경우 업데이트 알림 표시하지 않음
            if latest_version == skip_version:
                if not silent:
                    QMetaObject.invokeMethod(
                        self.parent,
                        "show_info_message",
                        Qt.QueuedConnection,
                        Q_ARG(str, "업데이트 건너뛰기"),
                        Q_ARG(str, f"버전 {latest_version}은(는) 건너뛰기로 설정되어 있습니다.")
                    )
                self.update_in_progress = False
                return
            
            if latest_version == self.current_version:
                if not silent:
                    QMetaObject.invokeMethod(
                        self.parent, 
                        "show_info_message", 
                        Qt.QueuedConnection,
                        Q_ARG(str, "업데이트 확인"), 
                        Q_ARG(str, "현재 최신 버전입니다.")
                    )
                self.update_in_progress = False
                return
            
            # 업데이트 가능한 버전이 있는 경우
            # GUI 스레드에 다이얼로그 표시 요청
            result = QMetaObject.invokeMethod(
                self.parent,
                "show_update_dialog",
                Qt.BlockingQueuedConnection,
                Q_RETURN_ARG(int),
                Q_ARG(str, latest_version),
                Q_ARG(str, release_notes)
            )
            
            if result != QMessageBox.Yes:
                self.update_in_progress = False
                return
            
            # 업데이트 파일 다운로드 및 설치
            self._download_and_install_update(latest_version)
            
        except Exception as e:
            if not silent and not self.cancel_requested:
                QMetaObject.invokeMethod(
                    self.parent,
                    "show_warning_with_copy",
                    Qt.QueuedConnection,
                    Q_ARG(str, "업데이트 오류"),
                    Q_ARG(str, f"업데이트 확인 중 오류가 발생했습니다: {str(e)}")
                )
            self.update_in_progress = False
    
    def _download_and_install_update(self, version):
        """업데이트 파일 다운로드 및 설치"""
        try:
            # 임시 디렉토리 생성
            self.temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(self.temp_dir, "update.zip")
            
            # 다운로드 진행 상황을 보여주는 다이얼로그 표시
            QMetaObject.invokeMethod(
                self.parent,
                "show_download_progress",
                Qt.QueuedConnection,
                Q_ARG(str, self.github_download_url),
                Q_ARG(str, zip_path)
            )
            
            # 파일 다운로드 (별도 스레드에서 실행)
            self._download_file(self.github_download_url, zip_path)
            
            # 취소 요청 확인
            if self.cancel_requested:
                self.update_in_progress = False
                return
            
            # 업데이트 파일 압축 해제 및 설치
            QMetaObject.invokeMethod(
                self.parent,
                "show_install_progress",
                Qt.QueuedConnection
            )
            
            # 압축 해제
            extract_dir = os.path.join(self.temp_dir, "extract")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 취소 요청이 있는지 다시 확인
            if self.cancel_requested:
                self.update_in_progress = False
                return
            
            # 업데이트 스크립트 생성
            self._create_update_script(extract_dir)
            
            # 애플리케이션 종료 및 업데이트 스크립트 실행
            QMetaObject.invokeMethod(
                self.parent,
                "restart_for_update",
                Qt.QueuedConnection
            )
            
        except Exception as e:
            if not self.cancel_requested:
                QMetaObject.invokeMethod(
                    self.parent,
                    "show_warning_with_copy",
                    Qt.QueuedConnection,
                    Q_ARG(str, "업데이트 설치 오류"),
                    Q_ARG(str, f"업데이트 설치 중 오류가 발생했습니다: {str(e)}")
                )
            
            # 임시 디렉토리 정리
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                
            self.update_in_progress = False

    def _download_file(self, url, destination):
        """파일 다운로드 함수 (취소 가능)"""
        try:
            # 스트림 방식으로 다운로드 (메모리 효율적)
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                # 다운로드 진행률 업데이트를 위한 변수
                downloaded = 0
                last_update = 0
                
                # 파일 쓰기
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.cancel_requested:
                            # 취소 요청이 있으면 중단
                            return
                            
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 진행률 업데이트 (10% 단위로)
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                if progress >= last_update + 5:
                                    last_update = progress
                                    QMetaObject.invokeMethod(
                                        self.parent,
                                        "update_download_progress",
                                        Qt.QueuedConnection,
                                        Q_ARG(int, progress)
                                    )
                # 다운로드 완료 시 100% 표시
                QMetaObject.invokeMethod(
                    self.parent,
                    "update_download_progress",
                    Qt.QueuedConnection,
                    Q_ARG(int, 100)
                )
        except Exception as e:
            if not self.cancel_requested:
                # 오류 메시지 표시 (취소된 경우 제외)
                QMetaObject.invokeMethod(
                    self.parent,
                    "show_warning_with_copy",
                    Qt.QueuedConnection,
                    Q_ARG(str, "다운로드 오류"),
                    Q_ARG(str, f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")
                )
    
    def cancel_update(self):
        """업데이트 취소"""
        self.cancel_requested = True
        
        # 임시 디렉토리 정리
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except:
                pass
                
        self.update_in_progress = False
    
    def _create_update_script(self, extract_dir):
        """업데이트 스크립트 생성 (현재 프로세스 종료 후 파일 복사 및 재시작)"""
        script_path = os.path.join(self.temp_dir, "update_script.bat")
        current_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        # 실행 파일 경로 확인
        if getattr(sys, 'frozen', False):
            # 패키징된 실행 파일인 경우
            executable = sys.executable  # 현재 실행 중인 EXE 파일 경로
            app_name = os.path.basename(executable)
            
            # 버전 번호 패턴이 있는지 확인 (예: EggManager_1.1.3.exe)
            base_name_pattern = re.search(r'(.*?)_[\d\.]+\.exe', app_name, re.IGNORECASE)
            if base_name_pattern:
                base_name = base_name_pattern.group(1)  # 기본 이름만 추출 (예: EggManager)
            else:
                base_name = os.path.splitext(app_name)[0]  # 확장자 제외한 이름
        else:
            # 스크립트로 실행 중인 경우
            executable = sys.executable
            app_path = os.path.abspath(sys.argv[0])
            app_name = os.path.basename(app_path)
            base_name = "python"
        
        # 새 실행 파일 찾기
        new_exe_files = [f for f in os.listdir(extract_dir) if f.lower().endswith('.exe')]
        
        if new_exe_files:
            # 새 EXE 파일이 있으면 사용
            new_exe_name = new_exe_files[0]
        else:
            # 새 EXE 파일이 없으면 이름 패턴 만들기
            new_exe_name = f"{base_name}.exe"  # 버전 번호 없이 기본 이름 사용
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write("@echo off\n")
            f.write("color 0A\n")  # 검정 바탕에 녹색 글자로 설정
            f.write("title EggManager 업데이트 진행 중...\n")
            f.write("mode con: cols=80 lines=30\n")  # 콘솔 창 크기 설정
            f.write("powershell -command \"$host.UI.RawUI.WindowTitle = 'EggManager 업데이트 진행 중...'\"\n")
            
            # 화면 지우기 및 헤더 표시
            f.write("cls\n")
            f.write("echo =============================================================\n")
            f.write("echo                 EggManager 업데이트 진행 중...              \n")
            f.write("echo =============================================================\n")
            f.write("echo.\n")
            f.write("echo 업데이트가 완료될 때까지 이 창을 닫지 마세요.\n")
            f.write("echo.\n")
            f.write("echo 1. 파일 백업 중...\n")
            
            # 기존 파일 백업
            f.write(f"if not exist \"{current_dir}\\backup\" mkdir \"{current_dir}\\backup\"\n")
            f.write(f"xcopy \"{current_dir}\\*.json\" \"{current_dir}\\backup\" /Y /Q\n")
            f.write(f"xcopy \"{current_dir}\\*.txt\" \"{current_dir}\\backup\" /Y /Q\n")
            f.write(f"xcopy \"{current_dir}\\*.ini\" \"{current_dir}\\backup\" /Y /Q\n")
            f.write(f"if exist \"{current_dir}\\resource\" xcopy \"{current_dir}\\resource\\*.json\" \"{current_dir}\\backup\" /Y /Q\n")
            
            f.write("echo 완료.\n")
            f.write("echo.\n")
            f.write("echo 2. 이전 실행 파일 이름 변경 중...\n")
            
            # 기존 EXE 파일 삭제 (실행 중인 파일은 삭제할 수 없으므로 이름 변경)
            f.write(f"if exist \"{current_dir}\\{app_name}\" ren \"{current_dir}\\{app_name}\" \"old_{app_name}.bak\"\n")
            
            f.write("echo 완료.\n")
            f.write("echo.\n")
            f.write("echo 3. 새 파일 복사 중...\n")
            
            # 새 파일 복사
            f.write(f"xcopy \"{extract_dir}\\*\" \"{current_dir}\" /E /Y /Q\n")
            
            f.write("echo 완료.\n")
            f.write("echo.\n")
            f.write("echo 4. 새 버전 실행 준비 중...\n")
            
            # 프로그램 재시작 - 실행 파일 이름 변경 처리
            f.write(f"if exist \"{current_dir}\\{new_exe_name}\" (\n")
            f.write("    echo 새 버전을 시작합니다...\n")
            f.write(f"    start \"\" \"{current_dir}\\{new_exe_name}\"\n")
            f.write("    echo.\n")
            f.write("    echo EggManager가 업데이트되었습니다!\n")
            f.write(f") else (\n")
            f.write("    echo.\n")
            f.write("    echo 새 실행 파일을 찾을 수 없습니다.\n")
            f.write("    echo 수동으로 프로그램을 실행해 주세요.\n")
            f.write("    echo.\n")
            f.write("    pause\n")
            f.write(f")\n")
            
            # 백업 파일 정리 (나중에 삭제)
            f.write("echo.\n")
            f.write("echo 5. 임시 파일 정리 중...\n")
            f.write(f"timeout /t 3 /nobreak >nul\n")
            f.write(f"if exist \"{current_dir}\\old_{app_name}.bak\" del \"{current_dir}\\old_{app_name}.bak\"\n")
            
            f.write("echo 완료!\n")
            f.write("echo.\n")
            f.write("echo =============================================================\n")
            f.write("echo                 업데이트가 완료되었습니다!                  \n")
            f.write("echo =============================================================\n")
            f.write("echo.\n")
            f.write("echo 이 창은 5초 후 자동으로 닫힙니다.\n")
            f.write("timeout /t 5\n")
            f.write("exit\n")
        
        return script_path

class PinManager:
    def __init__(self):
        self.filename = config["DEFAULT"]['pin_file']
        self.pins = self.load_pins()
        self.locked_pins = set()  # 잠긴 핀 목록을 저장할 세트
        self.txt_filename = config["DEFAULT"]['txt_file']
        self.log_filename = config["DEFAULT"]['log_file']
        self.locked_pins_file = os.path.join("resource", "locked_pins.json")  # 잠긴 핀 저장 파일
        self.stats_log_filename = os.path.join("resource", "pin_stats.json")  # 통계용 구조화된 로그 파일
        self.load_locked_pins()  # 잠긴 핀 정보 로드

    def load_pins(self):
        try:
            with open(self.filename, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        
    def show_log(self):
        try:
            with open(self.log_filename, "r") as log_file:
                log = log_file.read()
                log_file.close()
                return log
        except FileNotFoundError:
            return "로그 파일을 찾을 수 없습니다."
        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def save_pins(self):
        with open(self.filename, "w") as file:
            json.dump(self.pins, file, indent=4)
    
    def save_pins_to_txt(self):
        with open(self.txt_filename, "w") as file:
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                file.write(f"{idx}. {pin}: {balance}\n")

    # 로그 파일로부터 PIN과 원금을 사용하여 PIN 목록을 복구하는 함수
    def load_pins_from_log(self):
        try:
            with open(self.log_filename, "r") as log_file:
                log_lines = log_file.readlines()
                for line in log_lines:
                    match = re.search(r'(\d{5}-\d{5}-\d{5}-\d{5}) \[원금: (\d+)\]', line)
                    if match:
                        pin = match.group(1)
                        original_balance = int(match.group(2))
                        self.pins[pin] = original_balance
            self.save_pins()
            self.save_pins_to_txt()
            return "PIN 목록이 성공적으로 복구되었습니다."
        except FileNotFoundError:
            return "로그 파일을 찾을 수 없습니다."
        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def add_pin(self, pin, balance):
        self.pins[pin] = balance
        self.save_pins()
        self.save_pins_to_txt()
        return f"PIN {pin} 추가 완료. 잔액: {balance}"
    
    def format_pin(self, pin):
        pattern = re.compile(r'^\d{4}-\d{4}-\d{4}-\d{4}-\d{4}$')
        if bool(pattern.match(pin)):
            pin = self.unformat_pin(pin)
        if len(pin) == 20 and pin.isdigit():
            return f"{pin[:5]}-{pin[5:10]}-{pin[10:15]}-{pin[15:]}"
        return pin
    
    def unformat_pin(self, formatted_pin):
        return formatted_pin.replace("-", "")

    def is_valid_pin_format(self, pin):
        pattern = re.compile(r'^\d{5}-\d{5}-\d{5}-\d{5}$')
        return bool(pattern.match(pin))

    def delete_pin(self, pin):
        pin = self.format_pin(pin)
        if pin in self.pins:
            del self.pins[pin]
            if pin in self.locked_pins:
                self.locked_pins.remove(pin)
                self.save_locked_pins()
            self.save_pins()
            self.save_pins_to_txt()
            return f"PIN {pin} 삭제 완료."
        return f"PIN {pin}은(는) 존재하지 않습니다."
    
    def update_pin_balance(self, pin, new_balance):
        if pin in self.pins:
            self.pins[pin] = new_balance
            self.save_pins()
            self.save_pins_to_txt()
            return True
        return False

    def get_total_balance(self):
        return sum(self.pins.values())

    def list_pins(self):
        return list(self.pins.items())

    def find_pins_for_amount(self, amount, select_pins = []):
        if select_pins:
            # 선택된 핀 중에서 잠기지 않은 핀만 필터링
            filtered_pins = [(pin, balance) for pin, balance in select_pins if pin not in self.locked_pins]
            sorted_pins = sorted(filtered_pins, key=lambda x: x[1])
        else:
            # 모든 핀 중에서 잠기지 않은 핀만 필터링
            available_pins = [(pin, balance) for pin, balance in self.pins.items() if pin not in self.locked_pins]
            sorted_pins = sorted(available_pins, key=lambda x: x[1])

        selected_pins = []
        total_selected = 0
        best_combination = []
        best_total = 0

        # print("Sorted pins: ", sorted_pins)

        for pin, balance in sorted_pins:
            if total_selected >= amount:
                break
            selected_pins.append((pin, balance))
            total_selected += balance

        if total_selected >= amount and len(selected_pins) <= 5:
            # print("Selected pins: ", selected_pins)
            return selected_pins
        else:
            # 가능한 모든 조합을 고려하여 최적의 조합을 찾음
            for r in range(1, 6):
                for combination in combinations(sorted_pins, r):
                    total = sum(balance for pin, balance in combination)
                    if total >= amount and (best_total == 0 or total < best_total):
                        best_combination = combination
                        best_total = total

            if best_total >= amount:
                # print("Best combination: ", best_combination)
                return best_combination
    
        return []
    
    def pin_check(self, pin):
        pin = self.format_pin(pin)
        for pins in self.pins.keys():
            if pins == pin:
                return 1
        return 0
    
    def toggle_pin_lock(self, pin):
        """핀의 잠금 상태를 토글합니다"""
        if pin in self.locked_pins:
            self.locked_pins.remove(pin)
            self.save_locked_pins()
            return False  # 잠금 해제됨
        else:
            self.locked_pins.add(pin)
            self.save_locked_pins()
            return True  # 잠김

    def is_pin_locked(self, pin):
        """핀이 잠겨있는지 확인합니다"""
        return pin in self.locked_pins

    def save_locked_pins(self):
        """잠긴 핀 목록을 파일에 저장합니다"""
        # resource 폴더가 없으면 생성
        os.makedirs("resource", exist_ok=True)
        
        with open(self.locked_pins_file, "w") as file:
            json.dump(list(self.locked_pins), file, indent=4)
    
    def load_locked_pins(self):
        """잠긴 핀 목록을 파일에서 로드합니다"""
        try:
            with open(self.locked_pins_file, "r") as file:
                self.locked_pins = set(json.load(file))
        except (FileNotFoundError, json.JSONDecodeError):
            self.locked_pins = set()

    def load_stats_log(self):
        """통계용 구조화된 로그 파일을 불러옵니다."""
        try:
            with open(self.stats_log_filename, "r", encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            # 파일이 없거나 JSON 파싱 실패시 기본 구조 반환
            return {
                'total_amount': 0,
                'years': {}
            }
    
    def save_stats_log(self, stats_data):
        """통계용 구조화된 로그 파일을 저장합니다."""
        # resource 폴더가 없으면 생성
        os.makedirs(os.path.dirname(self.stats_log_filename) or '.', exist_ok=True)
        
        with open(self.stats_log_filename, "w", encoding='utf-8') as file:
            json.dump(stats_data, file, indent=4, ensure_ascii=False)
    
    def add_stats_log_entry(self, date_str, product_name, amount, pins_used):
        """통계용 로그에 새 항목을 추가합니다."""
        # 기존 로그 불러오기
        stats_data = self.load_stats_log()
        
        # 날짜 파싱
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month
        day = date_obj.day
        
        # 총 금액 업데이트
        stats_data['total_amount'] += amount
        
        # 연도별 통계 업데이트
        if str(year) not in stats_data['years']:
            stats_data['years'][str(year)] = {
                'year_amount': 0,
                'months': {}
            }
        stats_data['years'][str(year)]['year_amount'] += amount
        
        # 월별 통계 업데이트
        if str(month) not in stats_data['years'][str(year)]['months']:
            stats_data['years'][str(year)]['months'][str(month)] = {
                'month_amount': 0,
                'products': []
            }
        stats_data['years'][str(year)]['months'][str(month)]['month_amount'] += amount
        
        # 상품별 통계 추가
        stats_data['years'][str(year)]['months'][str(month)]['products'].append({
            'name': product_name,
            'amount': amount,
            'date': day,
            
            # 'pins_count': len(pins_used),
            # 'pins_info': pins_used  # [(pin, original_balance, used_amount, remaining)]
        })
        
        # 변경된 통계 저장
        self.save_stats_log(stats_data)
    
class PinManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = PinManager()
        self.auto_updater = AutoUpdater(current_version, self)
            
        self.current_theme = config['SETTING'].get('theme', 'Light')  # 기본값은 Light
        self.apply_theme(self.current_theme)
        self.initUI()
        # 메뉴바 이벤트 필터 설치
        self.menuBar().installEventFilter(self)
        # self.check_for_updates(silent=True)

        if config['SETTING']['auto_update'] == 'True':
            # print("자동 업데이트가 활성화되어 있습니다.")
            self.check_for_updates(silent=True)  # 자동 업데이트 확인

    def initUI(self):
        # UI 초기화 및 설정
        self.setWindowTitle(f"EggManager v{current_version}")
        self.setMinimumSize(600, 400)
        ico = 'resource/eggui.ico'
        self.setWindowIcon(QIcon(ico))

        # 메뉴 바 추가
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('설정')

        # 통계 메뉴 추가
        statistics_action = QAction('통계', self)
        statistics_action.triggered.connect(self.show_usage_statistics)
        menubar.addAction(statistics_action)  # 메뉴바에 직접 액션 추가

        # 프로그램 정보 액션 추가
        about_action = QAction('프로그램 정보', self)
        about_action.triggered.connect(self.show_about_dialog)
        settings_menu.addAction(about_action)

        # GitHub 릴리즈 페이지 액션 추가
        github_action = QAction('GitHub 페이지', self)
        github_action.triggered.connect(self.open_github_releases)
        settings_menu.addAction(github_action)

        # 로그 확인
        show_log = QAction('로그 보기', self)
        show_log.triggered.connect(self.show_log_file)
        settings_menu.addAction(show_log)

        # # 업데이트 액션 추가
        update_action = QAction('업데이트 확인', self)
        update_action.triggered.connect(self.check_for_updates)
        settings_menu.addAction(update_action)
        settings_menu.addSeparator()

        # 업데이트 메뉴 추가
        update_menu = QMenu('업데이트 설정', self)

        # # 자동 업데이트 확인 액션 추가
        settings_update = QAction('실행시 업데이트 확인', self, checkable=True)
        settings_update.setChecked(config['SETTING']['auto_update'] == 'True')
        settings_update.triggered.connect(self.update_settings_change)
        update_menu.addAction(settings_update)
        # settings_menu.addAction(settings_update)

        # 건너뛰기 설정 초기화 메뉴 추가
        reset_skip_action = QAction('업데이트 건너뛰기 설정 초기화', self)
        reset_skip_action.triggered.connect(self.reset_skip_version)
        update_menu.addAction(reset_skip_action)
        settings_menu.addMenu(update_menu)

        # 자동 제출 확인 액션 추가 
        settings_submit = QAction('자동 결제 활성화', self, checkable=True)
        settings_submit.setChecked(config['SETTING']['auto_submit'] == 'True')
        settings_submit.triggered.connect(self.auto_submit_settings_change)
        settings_menu.addAction(settings_submit)

        # 사이즈 조절
        settings_size_adjust = QAction('결제창 사이즈 자동 조절', self, checkable=True)
        settings_size_adjust.setChecked(config['SETTING']['size_adjust'] == 'True')
        settings_size_adjust.triggered.connect(self.size_adjust_change)
        settings_menu.addAction(settings_size_adjust)

        # 테마 메뉴 추가
        # theme_menu = QMenu('테마', self)
        theme_action = QAction('테마 선택', self)
        theme_action.triggered.connect(self.show_theme_selector)
        settings_menu.addAction(theme_action)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # PIN 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["PIN 번호", "잔액", "잠금"])
        self.table.verticalHeader().setVisible(False)
        # 각 컬럼의 크기 정책 개별 설정
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # PIN 번호 컬럼 - 늘어남
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 잔액 컬럼 - 늘어남
        self.table.resizeColumnsToContents()
        # 여기서 SingleSelection을 ExtendedSelection으로 변경
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # 행 단위 선택
        self.table.horizontalHeader().sectionClicked.connect(self.sort_pins)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # 버튼 배치
        button_layout = QHBoxLayout()
        btn_add = QPushButton("PIN 추가", self)
        btn_add.clicked.connect(self.add_pin)
        btn_add.setToolTip("새로운 PIN을 추가합니다.")
        button_layout.addWidget(btn_add)

        btn_delete = QPushButton("PIN 삭제", self)
        btn_delete.clicked.connect(self.delete_multiple_pins)  
        btn_delete.setToolTip("선택한 PIN을 모두 삭제합니다.")
        button_layout.addWidget(btn_delete)

        btn_use = QPushButton("PIN 자동 사용", self)
        btn_use.clicked.connect(self.use_pins)
        btn_use.setToolTip("선택한 금액을 사용할 수 있는 PIN을 자동으로 사용합니다.")
        button_layout.addWidget(btn_use)

        btn_restore = QPushButton("PIN 복구", self)
        btn_restore.clicked.connect(self.restore_pins)
        btn_restore.setToolTip("로그 파일로부터 PIN 목록을 복구합니다.")
        button_layout.addWidget(btn_restore)

        layout.addLayout(button_layout)

        bottom_layout = QHBoxLayout()
        self.sum = QLabel(f"잔액 : {'{0:,}'.format(self.manager.get_total_balance())}", self)
        bottom_layout.addWidget(self.sum)

        bottom_layout.addStretch(1)

        btn_quit = QPushButton("종료", self)
        btn_quit.clicked.connect(self.close)
        bottom_layout.addWidget(btn_quit)

        layout.addLayout(bottom_layout)

        self.update_table()

        # 테마 선택을 위한 서랍형 패널
        self.theme_dock = QDockWidget("테마 선택", self)
        self.theme_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.theme_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.theme_widget = QWidget()
        self.theme_layout = QVBoxLayout(self.theme_widget)
        
        self.light_radio = QRadioButton("Light", self.theme_widget)
        self.dark_radio = QRadioButton("Dark", self.theme_widget)
        self.theme_layout.addWidget(self.light_radio)
        self.theme_layout.addWidget(self.dark_radio)
        self.theme_layout.addStretch()

        self.light_radio.toggled.connect(lambda: self.apply_theme("Light"))
        self.dark_radio.toggled.connect(lambda: self.apply_theme("Dark"))
        
        if self.current_theme == "Light":
            self.light_radio.setChecked(True)
        else:
            self.dark_radio.setChecked(True)

        self.theme_dock.setWidget(self.theme_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.theme_dock)
        self.theme_dock.hide()

    def check_for_updates(self, silent=False):
        """사용자가 요청한 업데이트 확인"""
        self.auto_updater.check_for_updates_async(silent)

    @Slot(str, str)
    def show_info_message(self, title, message):
        """정보 메시지 표시 (스레드에서 호출 가능)"""
        QMessageBox.information(self, title, message)

    @Slot(str, str, result=int)
    def show_update_dialog(self, version, release_notes):
        """업데이트 대화상자 표시 (스레드에서 호출 가능)"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("업데이트 확인")
        msg_box.setText(f"새 버전 {version}이(가) 있습니다. 업데이트 하시겠습니까?")

        # 스크롤 영역 추가
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 가로 스크롤바 숨기기
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)  # 여백 추가

        # 업데이트 내용 헤더와 본문 분리
        notes_header = QLabel(f"<b>새 버전 {version}이(가) 있습니다. 업데이트 하시겠습니까?</b>")
        notes_header.setAlignment(Qt.AlignLeft)
        scroll_layout.addWidget(notes_header)
        scroll_layout.addSpacing(20)  # 헤더와 본문 사이에 여백 추가

        # 업데이트 내용
        release_notes_label = QLabel(release_notes)
        release_notes_label.setWordWrap(True)
        release_notes_label.setTextFormat(Qt.MarkdownText)  # 마크다운 지원 (GitHub 형식)
        release_notes_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        release_notes_label.setOpenExternalLinks(True)  # 링크 클릭 가능하게
        release_notes_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)  # 텍스트 선택 가능
        scroll_layout.addWidget(release_notes_label)

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setMinimumSize(400, 250)  # 스크롤 영역 크기 키움
        scroll_area.setFrameStyle(QFrame.NoFrame)  # 테두리 제거

        # 메시지 박스 레이아웃에 스크롤 영역 추가
        layout = msg_box.layout()
        layout.addWidget(scroll_area, 0, 0, 1, layout.columnCount())
        layout.setRowStretch(0, 0)
        layout.setRowStretch(layout.rowCount(), 1)

        # 버튼 추가
        # msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # msg_box.setDefaultButton(QMessageBox.Yes)
        # return msg_box.exec()
        # 버튼 추가 - 업데이트, 건너뛰기, 취소
        update_button = msg_box.addButton("업데이트", QMessageBox.YesRole)
        skip_button = msg_box.addButton("이 버전 건너뛰기", QMessageBox.ActionRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        
        msg_box.setDefaultButton(update_button)
        msg_box.exec()
        
        # 클릭된 버튼 확인
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == update_button:
            return QMessageBox.Yes
        elif clicked_button == skip_button:
            # 건너뛰기 버튼이 클릭된 경우 건너뛸 버전 설정 저장
            self.skip_version(version)
            return QMessageBox.No
        else:  # 취소 버튼
            return QMessageBox.No

    @Slot(str, str)
    def show_download_progress(self, url, path):
        """다운로드 진행 상황 다이얼로그 표시 (취소 버튼 기능 추가)"""
        self.progress_dialog = QProgressDialog("업데이트 파일 다운로드 중...", "취소", 0, 100, self)
        self.progress_dialog.setWindowTitle("다운로드")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setMinimumDuration(0)
        
        # 취소 버튼 연결
        self.progress_dialog.canceled.connect(self.cancel_download)

        self.download_completed = False
        
        # 취소 요청 시 실행할 함수 정의
        self.progress_dialog.show()
        
        # 진행 상황 업데이트를 위한 타이머 설정
        self.download_timer = QTimer(self)
        self.download_timer.timeout.connect(lambda: self.progress_dialog.setValue(self.progress_dialog.value() + 5 if self.progress_dialog.value() < 95 else 95))
        self.download_timer.start(200)  # 200ms마다 업데이트
        
        return QDialog.Accepted  # 다이얼로그 표시 성공
    
    @Slot(int)
    def update_download_progress(self, progress):
        """다운로드 진행 상황 업데이트"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(progress)

            if progress >= 100 and hasattr(self, 'download_timer'):
                self.download_timer.stop()
                self.download_completed = True  # 다운로드 완료 플래그 설정

    def cancel_download(self):
        """다운로드 취소 처리"""
        # 다운로드가 완료된 상태면 취소 처리하지 않음
        if hasattr(self, 'download_completed') and self.download_completed:
            return

        if hasattr(self, 'download_timer') and self.download_timer.isActive():
            self.download_timer.stop()
        
        # AutoUpdater에 취소 요청 전달
        self.auto_updater.cancel_update()
        
        # 다이얼로그 닫기
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # 취소 알림
        if not self.auto_updater.update_completed:
            QMessageBox.information(self, "업데이트 취소", "업데이트가 취소되었습니다.")

    @Slot()
    def show_install_progress(self):
        """설치 진행 상황 다이얼로그 표시"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText("업데이트 파일 설치 중...")
            self.progress_dialog.setValue(100)
            # 취소 버튼 비활성화 - 설치 단계에서는 취소 불가
            self.download_completed = True
            self.progress_dialog.setCancelButtonText("설치 중...")
            self.progress_dialog.setCancelButton(None)
            self.auto_updater.update_completed = True  # 업데이트 완료 플래그 설정
        
        if hasattr(self, 'download_timer') and self.download_timer.isActive():
            self.download_timer.stop()

    @Slot()
    def restart_for_update(self):
        """업데이트 후 재시작"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # 업데이트 확인
        if self.auto_updater.cancel_requested:
            return  # 취소된 경우 재시작하지 않음
        
        # 업데이트 스크립트 실행
        script_path = os.path.join(self.auto_updater.temp_dir, "update_script.bat")
        if os.path.exists(script_path):
            try:
                # 현재 작업 중인 내용 저장
                self.manager.save_pins()
                
                # 업데이트 스크립트를 별도 프로세스로 실행
                subprocess.Popen(
                    [script_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                # 현재 애플리케이션 종료
                QApplication.quit()
            except Exception as e:
                self.show_warning_with_copy("업데이트 오류", f"업데이트 스크립트 실행 중 오류가 발생했습니다: {str(e)}")

    def skip_version(self, version):
        """특정 버전 업데이트를 건너뛰도록 설정"""
        # 건너뛸 버전을 config에 저장
        config['UPDATE']['skip_version'] = version
        # 설정 파일에 변경 사항 저장
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        
        QMessageBox.information(
            self, 
            "업데이트 건너뛰기", 
            f"버전 {version}은(는) 다음 업데이트까지 알림이 표시되지 않습니다."
        )

    def reset_skip_version(self):
        """건너뛰기로 설정된 버전 설정 초기화"""
        current_skip = config['UPDATE'].get('skip_version', '')
        
        if not current_skip:
            QMessageBox.information(self, "설정 초기화", "건너뛰기로 설정된 버전이 없습니다.")
            return
            
        # 사용자 확인
        reply = QMessageBox.question(
            self, 
            "설정 초기화", 
            f"현재 건너뛰기로 설정된 버전 {current_skip}에 대한 설정을 초기화하시겠습니까?\n"
            "초기화하면 다음 실행 시 업데이트 알림이 표시됩니다.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            config['UPDATE']['skip_version'] = ''
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            QMessageBox.information(self, "설정 초기화 완료", "업데이트 건너뛰기 설정이 초기화되었습니다.")

    def show_theme_selector(self):
        self.theme_dock.show()

    def apply_theme(self, theme):
        try:
            if theme == "Light":
                light = 'resource/dracula_light.qss'
                with open(light, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
            else:  # Dark
                dark = 'resource/dracula.qss'
                with open(dark, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
            self.current_theme = theme
            config['SETTING']['theme'] = theme
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"{theme} theme file not found.")

    # 프로그램 정보 다이얼로그
    def show_about_dialog(self):
        # 프로그램 정보 대화 상자 표시
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("프로그램 정보")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"EggManager v{current_version}"))
        layout.addWidget(QLabel("개발자: TUVup"))
        layout.addWidget(QLabel("이 프로그램은 에그머니 PIN 관리를 위한 도구입니다."))
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        about_dialog.setLayout(layout)
        about_dialog.exec()

    # 금액 입력 다이얼로그
    def amount_input_dialog(self, title="금액 입력"):
        input_dialog = QDialog(self)
        input_dialog.setWindowTitle(title)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("금액을 입력하세요."))
        amount_input = QSpinBox()
        amount_input.setWrapping(True)
        amount_input.setRange(0, 500000)
        amount_input.setValue(0)
        amount_input.selectAll()
        amount_input.setSingleStep(1000)
        layout.addWidget(amount_input)
        amount_radio1 = QRadioButton("1000")
        amount_radio2 = QRadioButton("3000")
        amount_radio3 = QRadioButton("5000")
        amount_radio4 = QRadioButton("10000")
        amount_radio5 = QRadioButton("30000")
        amount_radio6 = QRadioButton("50000")
        amount_radio1.clicked.connect(lambda: amount_input.setValue(1000))
        amount_radio2.clicked.connect(lambda: amount_input.setValue(3000))
        amount_radio3.clicked.connect(lambda: amount_input.setValue(5000))
        amount_radio4.clicked.connect(lambda: amount_input.setValue(10000))
        amount_radio5.clicked.connect(lambda: amount_input.setValue(30000))
        amount_radio6.clicked.connect(lambda: amount_input.setValue(50000))
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(amount_radio1)
        radio_layout.addWidget(amount_radio2)
        radio_layout.addWidget(amount_radio3)
        radio_layout.addWidget(amount_radio4)
        radio_layout.addWidget(amount_radio5)
        radio_layout.addWidget(amount_radio6)
        layout.addLayout(radio_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(input_dialog.accept)
        button_box.rejected.connect(input_dialog.reject)
        layout.addWidget(button_box)
        input_dialog.setLayout(layout)
        if input_dialog.exec() == QDialog.Accepted:
            return amount_input.value(), True
        return None, False
    
    def show_usage_statistics(self):
        """PIN 사용 통계를 표시합니다."""
        try:
            # 통계 데이터 로드
            stats_data = self.manager.load_stats_log()
            
            # 통계 다이얼로그 생성
            stats_dialog = QDialog(self)
            stats_dialog.setWindowTitle("PIN 사용 통계")
            stats_dialog.setMinimumSize(500, 400)
            stats_dialog.setMaximumSize(500, 400)
            
            # 레이아웃 설정
            layout = QVBoxLayout(stats_dialog)
            
            # 스크롤 영역 설정
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setAlignment(Qt.AlignTop)
            
            # 총 누적 금액 표시
            total_amount = stats_data.get('total_amount', 0)
            total_label = QLabel(f"<h2>총 누적 금액: {'{0:,}'.format(total_amount)}원</h2>")
            scroll_layout.addWidget(total_label)
            
            # 연도별 통계 표시
            years = sorted(stats_data.get('years', {}).keys(), reverse=True)
            for year in years:
                year_stats = stats_data['years'][year]
                year_label = QLabel(f"<h3>{year}년 (연간 사용 금액: {'{0:,}'.format(year_stats['year_amount'])}원)</h3>")
                scroll_layout.addWidget(year_label)
                
                # 월별 통계 표시 (내림차순)
                months = sorted(year_stats.get('months', {}).keys(), reverse=True)
                for month in months:
                    month_stats = year_stats['months'][month]
                    month_label = QLabel(f"<h4>{month}월 (월간 사용 금액: {'{0:,}'.format(month_stats['month_amount'])}원)</h4>")
                    # month_label.setStyleSheet("color: #333; margin-left: 20px;")
                    month_label.setStyleSheet("margin-left: 20px;")
                    scroll_layout.addWidget(month_label)
                    
                    # 상품별 통계 표시
                    products = sorted(month_stats.get('products', []), key=lambda x: x['date'], reverse=True)
                    for product in products:
                        product_label = QLabel(f"{product['date']}일: {product['name']} - {'{0:,}'.format(product['amount'])}원")
                        product_label.setStyleSheet("margin-left: 40px;")
                        scroll_layout.addWidget(product_label)
                
                # 연도 간 구분선 추가
                if year != years[-1]:  # 마지막 연도가 아니면 구분선 추가
                    line = QFrame()
                    line.setFrameShape(QFrame.HLine)
                    line.setFrameShadow(QFrame.Sunken)
                    scroll_layout.addWidget(line)
            
            # 데이터가 없는 경우 안내 메시지 표시
            if not years:
                no_data_label = QLabel("사용 내역이 없습니다.")
                scroll_layout.addWidget(no_data_label)
            
            # 스크롤 영역 완성
            scroll_area.setWidget(scroll_content)
            layout.addWidget(scroll_area)
            
            # 닫기 버튼 추가
            close_button = QPushButton("닫기")
            close_button.clicked.connect(stats_dialog.accept)
            layout.addWidget(close_button)
            
            # 다이얼로그 표시
            stats_dialog.exec()
        except Exception as e:
            self.show_warning_with_copy("통계 오류", f"통계 정보를 불러오는 중 오류가 발생했습니다: {str(e)}")

    @Slot(str, str)
    def show_warning_with_copy(self, title, message):
        """복사 기능이 포함된 경고 메시지 표시"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # 복사 버튼 추가
        copy_button = msg_box.addButton("복사", QMessageBox.ActionRole)
        ok_button = msg_box.addButton(QMessageBox.Ok)
        msg_box.setDefaultButton(ok_button)
        
        # 메시지박스 표시
        msg_box.exec()
        
        # 복사 버튼이 클릭되었는지 확인
        if msg_box.clickedButton() == copy_button:
            pyperclip.copy(message)
            QMessageBox.information(self, "복사 완료", "오류 메시지가 클립보드에 복사되었습니다.")
        
        return msg_box.standardButton(msg_box.clickedButton())
    
    def mousePressEvent(self, event):
        # 테이블 위치와 크기 정보 가져오기
        table_rect = self.table.geometry()
        
        # 클릭한 위치가 테이블 영역 내부인지 확인
        # pos() 대신 position().toPoint() 사용
        if not table_rect.contains(event.position().toPoint()):
            # 테이블 외부를 클릭한 경우 선택 해제
            self.table.clearSelection()
        
        # 부모 클래스의 이벤트 처리 메서드 호출
        super().mousePressEvent(event)
    
    def eventFilter(self, obj, event):
        # 메뉴바에 대한 마우스 버튼 누름 이벤트 처리
        if obj == self.menuBar() and event.type() == QEvent.MouseButtonPress:
            # 테이블 선택 해제
            self.table.clearSelection()
            
        # 이벤트를 기본 핸들러로 전달
        return super().eventFilter(obj, event)
    
    def open_github_releases(self):
        # GitHub 릴리즈 페이지 열기
        webbrowser.open("https://github.com/TUVup/EggPinManager")
    
    def show_log_file(self):
        log = self.manager.show_log()
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("로그")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{log}"))
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(about_dialog.accept)
        layout.addWidget(button_box)
        about_dialog.setLayout(layout)
        about_dialog.exec()
    
    
    # 자동 업데이트 설정 변경
    def update_settings_change(self):
        if config['SETTING']['auto_update'] == 'True':
            config['SETTING']['auto_update'] = 'False'
        else:
            config['SETTING']['auto_update'] = 'True'
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    
    def auto_submit_settings_change(self):
        if config['SETTING']['auto_submit'] == 'True':
            config['SETTING']['auto_submit'] = 'False'
        else:
            config['SETTING']['auto_submit'] = 'True'
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)

    def size_adjust_change(self):
        if config['SETTING']['size_adjust'] == 'True':
            config['SETTING']['size_adjust'] = 'False'
        else:
            config['SETTING']['size_adjust'] = 'True'
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    
    # PIN 목록을 로그 파일로부터 복구하는 함수
    def restore_pins(self):
        reply = QMessageBox.question(self, "PIN 복구", "PIN 목록을 로그 파일로부터 복구하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            result = self.manager.load_pins_from_log()
            QMessageBox.information(self, "PIN 복구", result)
            self.update_table()

    # 테이블 위젯에 컨텍스트 메뉴 추가
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        add_action = QAction("PIN 추가", self)
        add_action.triggered.connect(self.add_pin)
        context_menu.addAction(add_action)

        edit_balance_action = QAction("잔액 수정", self)
        edit_balance_action.triggered.connect(self.edit_selected_pin_balance)
        context_menu.addAction(edit_balance_action)

        # 잠금/해제 메뉴 추가
        lock_action = QAction("PIN 잠금/해제", self)
        lock_action.triggered.connect(self.toggle_selected_pin_lock)
        context_menu.addAction(lock_action)

        delete_action = QAction("PIN 삭제", self)
        delete_action.triggered.connect(self.delete_selected_pin)
        context_menu.addAction(delete_action)

        multiple_delete_action = QAction("여러 PIN 삭제", self)
        multiple_delete_action.triggered.connect(self.delete_multiple_pins)
        context_menu.addAction(multiple_delete_action)

        context_menu.exec(self.mapToGlobal(event.pos()))

    def toggle_selected_pin_lock(self):
        """선택된 핀의 잠금 상태를 토글합니다"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "오류", "잠금/해제할 PIN을 선택해 주세요.")
            return
            
        selected_rows = set([item.row() for item in selected_items])
        for row in selected_rows:
            pin = self.table.item(row, 0).text()
            self.manager.toggle_pin_lock(pin)
            
        QMessageBox.information(self, "완료", f"{len(selected_rows)}개의 PIN 잠금 상태가 변경되었습니다.")
        self.update_table()

    # 테이블에서 선택된 핀을 삭제하는 기능
    def delete_selected_pin(self):
        selected_items = self.table.currentItem()
        if selected_items:
            cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if cancel == QMessageBox.Yes:
                pin = self.table.item(selected_items.row(), 0).text()
                result = self.manager.delete_pin(pin)
                QMessageBox.information(self, "결과", result)
                self.update_table()
    
    # 여러 PIN을 동시에 삭제하는 기능
    def delete_multiple_pins(self):
        # 선택된 행 가져오기
        selected_rows = set([item.row() for item in self.table.selectedItems()])
        
        if not selected_rows:
            QMessageBox.warning(self, "오류", "삭제할 PIN을 선택해 주세요.")
            return
        
        # 선택된 PIN 목록 생성
        selected_pins = []
        for row in selected_rows:
            pin = self.table.item(row, 0).text()
            selected_pins.append(pin)
        
        # 사용자에게 삭제 확인 메시지 표시
        message = f"선택한 {len(selected_pins)}개의 PIN을 삭제하시겠습니까?\n\n"
        if len(selected_pins) <= 5:  # 5개 이하면 목록 표시
            message += "PIN 목록:\n" + "\n".join(selected_pins)
        else:  # 5개 초과면 일부만 표시
            message += "PIN 목록 (일부):\n" + "\n".join(selected_pins[:5]) + f"\n... 외 {len(selected_pins)-5}개"
        
        ok = QMessageBox.question(self, "PIN 삭제", message, QMessageBox.Yes | QMessageBox.No)
        
        if ok != QMessageBox.Yes:
            return
        
        # 최종 확인
        final_ok = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if final_ok != QMessageBox.Yes:
            return
        
        # PIN 삭제 진행
        deleted_count = 0
        for pin in selected_pins:
            if self.manager.pin_check(pin) == 1:
                self.manager.delete_pin(pin)
                deleted_count += 1
        
        # 결과 메시지 표시
        QMessageBox.information(self, "결과", f"{deleted_count}개의 PIN이 삭제되었습니다.")
        self.update_table()
    
    # 테이블에서 선택된 핀의 잔액을 수정하는 기능
    def edit_selected_pin_balance(self):
        selected_items = self.table.currentItem()
        if selected_items:
            pin = self.table.item(selected_items.row(), 0).text()
            # new_balance, ok = QInputDialog.getInt(self, "잔액 수정", "새 잔액 입력:", 0)
            new_balance, ok = self.amount_input_dialog('잔액 수정')
            if not ok:
                QMessageBox.warning(self, "취소", "잔액 수정이 취소되었습니다.")
                return
            if ok and new_balance <= 0:
                QMessageBox.warning(self, "오류", "잔액은 0보다 커야 합니다.")
                return
            if ok:
                result = self.manager.update_pin_balance(pin, new_balance)
                QMessageBox.information(self, "성공", "잔액 수정이 완료되었습니다.")
                self.update_table()

    def update_table(self):
        self.sum.setText(f"잔액 : {'{0:,}'.format(self.manager.get_total_balance())}")
        pins = self.manager.list_pins()
        self.table.setRowCount(len(pins))
        for row, (pin, balance) in enumerate(pins):
            # PIN 번호 열
            self.table.setItem(row, 0, QTableWidgetItem(pin))
            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            
            # 잔액 열
            self.table.setItem(row, 1, QTableWidgetItem('{0:,}'.format(balance)))
            self.table.item(row, 1).setTextAlignment(Qt.AlignCenter)
            
            # 잠금 상태 열 - 체크박스 위젯 사용
            checkbox = QCheckBox()
            checkbox.setChecked(self.manager.is_pin_locked(pin))
            checkbox.stateChanged.connect(lambda state, p=pin: self.toggle_pin_lock(p, state))

            # 체크박스 레이아웃 최적화
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_widget.setLayout(checkbox_layout)
            checkbox_widget.setStyleSheet("background-color: transparent;")

            self.table.setCellWidget(row, 2, checkbox_widget)

            # 잠긴 핀에 시각적 표시 추가 (회색 배경과 이탤릭체)
            if self.manager.is_pin_locked(pin):
                # for col in range(2):  # 첫 두 열만 스타일 적용 (체크박스 제외)
                item = self.table.item(row, 0)
                item2 = self.table.item(row, 1)
                font = item.font()
                font2 = item2.font()
                font.setItalic(True)
                font2.setItalic(True)
                font.setStrikeOut(True)
                font2.setStrikeOut(True)
                item.setFont(font)
                item2.setFont(font2)
                # item.setForeground(QColor(128, 128, 128))  # 회색 텍스트
                # item.setBackground(QColor(240, 240, 240))  # 연한 회색 배경
            else:
                # 잠긴 핀이 아닌 경우 스타일 초기화
                item = self.table.item(row, 0)
                item2 = self.table.item(row, 1)
                font = item.font()
                font2 = item2.font()
                font.setItalic(False)
                font2.setItalic(False)
                font.setStrikeOut(False)
                font2.setStrikeOut(False)
                item.setFont(font)
                item2.setFont(font2)

        # PinManagerApp 클래스에 추가
    def toggle_pin_lock(self, pin, state):
        """핀의 잠금 상태를 토글합니다"""
        self.manager.toggle_pin_lock(pin)

        self.update_table()
    
    sort_flag = 0
    
    def sort_pins(self):
        """잔액을 기준으로 PIN 목록을 정렬하는 함수"""
        if self.sort_flag == 0:
            self.manager.pins = dict(sorted(self.manager.pins.items(), key=lambda x: x[1]))
            self.sort_flag = 1
        else:
            self.manager.pins = dict(sorted(self.manager.pins.items(), key=lambda x: x[1], reverse=True))
            self.sort_flag = 0
        self.update_table()

    # PIN 추가 다이얼로그
    def add_pin(self):
        pin, ok = QInputDialog.getText(self, "PIN 추가", "PIN 입력 (핀 전체 또는 숫자만 입력):")
        pin = self.manager.format_pin(pin)
        if self.manager.pin_check(pin) == 1:
            QMessageBox.warning(self, "PIN오류", "중복된 PIN입니다.")
        elif not self.manager.is_valid_pin_format(pin) and ok:
            QMessageBox.warning(self, "오류", "올바른 PIN 형식이 아닙니다.")
        elif ok and pin:
            balance, ok = self.amount_input_dialog()
            if ok and balance > 0:
                result = self.manager.add_pin(pin, balance)
                QMessageBox.information(self, "결과", result)
                self.update_table()
            elif ok and balance <= 0:
                QMessageBox.warning(self, "금액 오류", "0보다 작은 금액은 입력할 수 없습니다.")
            elif ok and not balance:
                QMessageBox.warning(self, "금액 오류", "금액은 반드시 입력해야 합니다.")

    # PIN 삭제 다이얼로그
    def delete_pin(self):
        # pin, ok = QInputDialog.getText(self, "PIN 삭제", "삭제할 PIN 입력:")
        selected_items = self.table.currentItem()
        if not selected_items:
            QMessageBox.warning(self, "오류", "삭제할 PIN을 선택해 주세요.")
            return
        pin = self.table.item(selected_items.row(), 0).text()
        ok = QMessageBox.question(self, "PIN 삭제", f"PIN: {pin}을 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        if ok and pin:
            if 0 == self.manager.pin_check(pin):
                QMessageBox.warning(self, "PIN오류", "존재하지 않는 PIN입니다.")
            else:
                cancel = QMessageBox.warning(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
                if cancel == QMessageBox.Yes:
                    result = self.manager.delete_pin(pin)
                    QMessageBox.information(self, "결과", result)
                    self.update_table()

    # PIN 자동 사용 기능
    def use_pins(self):
        # 사용 방법 선택 다이얼로그
        selectbox = QMessageBox(self)
        selectbox.setIcon(QMessageBox.Question)
        selectbox.setWindowTitle("PIN 자동 사용")
        
        # 선택된 행이 있는지 확인
        selected_rows = set([item.row() for item in self.table.selectedItems()])
        
        if selected_rows:
            selectbox.setWindowTitle("선택된 PIN 자동 사용")
            pin_num = []
            locked_pin_count = 0
            
            # 선택된 핀 중 잠기지 않은 핀만 필터링
            filtered_rows = []
            for row in selected_rows:
                pin = self.table.item(row, 0).text()
                if not self.manager.is_pin_locked(pin):
                    pin_num.append(pin)
                    filtered_rows.append(row)
                else:
                    locked_pin_count += 1
            
            # 선택된 핀이 모두 잠겨 있는 경우
            if not pin_num:
                QMessageBox.warning(self, "오류", "선택된 PIN이 모두 잠겨 있습니다.")
                return
            message = ""
            # 일부 핀이 잠겨 있는 경우 알림
            if locked_pin_count > 0:
                message += f"선택된 PIN 중 {locked_pin_count}개는 잠겨 있어 사용되지 않습니다.\n"
            if len(pin_num) <= 5:  # 5개 이하면 목록 표시
                message += "사용될 PIN 목록:\n" + "\n".join(pin_num)
            else:  # 5개 초과면 일부만 표시
                message += "사용될 PIN 목록 (일부):\n" + "\n".join(pin_num[:5]) + f"\n... 외 {len(pin_num)-5}개"
            selectbox.setText("\n사용 방법을 선택하세요.\n" + message + "\n사용가능한 총 금액: " + str('{0:,}'.format(sum(int(self.table.item(row, 1).text().replace(',', '')) for row in filtered_rows))) + "원")
            # PIN이 선택되었을 때 "선택된 PIN 사용" 버튼 추가
            # selected_pins = QPushButton("선택된 PIN 사용")
            # selectbox.addButton(selected_pins, QMessageBox.AcceptRole)
        else:
            selectbox.setText("\n사용 방법을 선택하세요.\n")
            
        browser = QPushButton("브라우저")
        ingame = QPushButton("HAOPLAY")
        cancel = QPushButton("취소")
        selectbox.addButton(browser, QMessageBox.AcceptRole)
        selectbox.addButton(ingame, QMessageBox.AcceptRole)
        selectbox.addButton(cancel, QMessageBox.RejectRole)

        selectbox.exec()
        
        clicked_button = selectbox.clickedButton()

        if selected_rows:
            selected_pins_data = []
            for row in filtered_rows:
                pin = self.table.item(row, 0).text()
                balance = int(self.table.item(row, 1).text().replace(',', ''))
                selected_pins_data.append((pin, balance))

            if clicked_button == browser:
                # 브라우저 사용
                result = self.use_selected_pins_browser(selected_pins_data)
                if isinstance(result, str) and ("❌" in result or "오류" in result or "실패" in result):
                    self.show_warning_with_copy("오류", result)
                else:
                    QMessageBox.information(self, "결과", result)
                self.update_table()
            elif clicked_button == ingame:
                # HAOPLAY 사용
                result = self.use_selected_pins_auto(selected_pins_data)
                if isinstance(result, str) and ("❌" in result or "오류" in result or "실패" in result):
                    self.show_warning_with_copy("오류", result)
                else:
                    QMessageBox.information(self, "결과", result)
                self.update_table()
        elif clicked_button == ingame:
            ok = QMessageBox.question(self, "인게임 결제", "인게임 자동 결제를 사용하시겠습니까?")
            if ok == QMessageBox.Yes:
                result = self.use_pins_auto()
                if isinstance(result, str) and ("❌" in result or "오류" in result or "실패" in result):
                    self.show_warning_with_copy("오류", result)
                else:
                    QMessageBox.information(self, "결과", result)
                self.update_table()
        elif clicked_button == browser:
            amount, ok = QInputDialog.getInt(self, "브라우저 PIN 자동 채우기", "사용할 금액 입력:", step=1000)
            if ok and amount > 0:
                result = self.use_pins_browser(amount)
                if isinstance(result, str) and ("❌" in result or "오류" in result or "실패" in result):
                    self.show_warning_with_copy("오류", result)
                else:
                    QMessageBox.information(self, "결과", result)
                self.update_table()

    # 선택된 PIN을 브라우저에서 사용
    def use_selected_pins_browser(self, selected_pins):
        if not selected_pins:
            return "선택된 PIN이 없습니다."
        
        total_balance = sum(balance for _, balance in selected_pins)

        amount, ok = QInputDialog.getInt(self, "브라우저 PIN 자동 채우기", 
                          f"사용할 금액 입력 (최대 {total_balance}원):", 
                          0, 1, total_balance, 1000)
        
        selected_pins = self.manager.find_pins_for_amount(amount, selected_pins)
        
        if not ok:
            return "취소되었습니다."
        
        if amount <= 0:
            return "올바른 금액을 입력하세요."
        
        if amount > total_balance:
            return "선택된 PIN의 총 잔액보다 큰 금액을 사용할 수 없습니다."
        
        QMessageBox.information(self, "준비", f"{amount}원을 사용하기 위해 {len(selected_pins)}개의 PIN을 사용합니다.")
        if len(selected_pins) > 1:
            QMessageBox.information(self, "준비", f"핀 입력창을 {len(selected_pins)-1}개 추가해 주세요.")
        QMessageBox.information(self, "준비", "첫번째 핀 입력창의 첫번째 칸을 클릭하고 PIN이 입력될 준비를 하세요.\n3초 후 시작합니다.")
        time.sleep(3)
        
        total_used = 0
        new_log_entry = '브라우저 자동사용 - ' + str(amount) + '원\n'
        pins_used_info = []  # 통계 로그용 정보 수집

        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            pyautogui.write(pin.replace("-", ""))  # PIN 입력
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            pins_used_info.append((pin, balance, used_amount, remaining_balance))
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        # self.log_pin_usage(new_log_entry)
        self.log_pin_usage(new_log_entry, "브라우저 자동사용", amount, pins_used_info)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()
        self.table.clearSelection()

        return f"선택된 PIN {len(selected_pins)}개로 {amount}원 사용이 완료되었습니다."

    # 선택된 PIN을 HAOPLAY에서 사용
    def use_selected_pins_auto(self, selected_pins):
        if config['SETTING']['size_adjust'] == 'True':
            self.adjust_window_size()
            time.sleep(1)  # 창 크기 조절 후 잠시 대기
        # 현재 클립보드 데이터 저장
        original_clipboard = pyperclip.paste()
        total_used = 0
        new_log_entry = ""
        pins_used_info = []  # 통계 로그용 정보 수집
        
        try:
            # 1️⃣ HAOPLAY 창 핸들 찾기
            haoplay_hwnd = user32.FindWindowW(None, "HAOPLAY")
            if not haoplay_hwnd:
                return "❌ HAOPLAY 창을 찾을 수 없습니다."

            # 2️⃣ "Chrome_WidgetWin_0" 컨트롤 핸들 찾기 (웹뷰 컨트롤)
            webview_hwnd = user32.FindWindowExW(haoplay_hwnd, 0, "Chrome_WidgetWin_0", None)
            if not webview_hwnd:
                return "❌ 웹뷰 컨트롤을 찾을 수 없습니다."

            # 3️⃣ 창 활성화 (child_hWnd로 변경)
            user32.SetForegroundWindow(webview_hwnd)  # 웹뷰 컨트롤을 최상위로 활성화
            time.sleep(0.5)  # 안정성을 위해 대기
            
            pyautogui.hotkey('ctrl', 'shift', 'j')  # DevTools 열기
            time.sleep(1)
            pyautogui.hotkey('ctrl', '`') # Console 탭으로 이동
            time.sleep(0.2)

            # amount = int(self.find_amount())
            amount = self.find_amount()
            product_name = self.find_Product()
            new_log_entry += f'{product_name} - {amount}원\n'

            # 선택된 PIN의 총 잔액 확인
            total_balance = sum(balance for _, balance in selected_pins)
            if total_balance < amount:
                return f"선택된 PIN의 총 잔액({total_balance}원)이 필요한 금액({amount}원)보다 적습니다."

            # 목록에서 최대 5개의 핀번호 제한
            pins_to_use = self.manager.find_pins_for_amount(amount, selected_pins)
            if not pins_to_use:
                return "충분한 잔액이 없습니다."
            if len(pins_to_use) == 0:
                return "사용할 수 있는 핀 조합이 없습니다."
            
            pins_to_inject = [pin for pin, _ in pins_to_use]

            # 4️⃣ 핀번호를 입력박스에 추가
            self.add_pin_input_box(len(pins_to_inject))

            # 5️⃣ 핀번호들 자바스크립트를 통해 입력
            self.inject_pin_codes(pins_to_inject)

            # 모두 동의
            self.click_all_agree()

            # 제출
            if config['SETTING']['auto_submit'] == 'True':
                self.submit()

        except Exception as e:
            return f"❌ 자동 입력에 실패했습니다.\n{e}"

        finally:
            # 클립보드 데이터 원래 값으로 복원
            pyperclip.copy(original_clipboard)

        # 사용한 핀의 잔액을 갱신하고 필요 시 PIN 삭제
        for pin, balance in pins_to_use:
            if total_used >= amount:
                break
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            pins_used_info.append((pin, balance, used_amount, remaining_balance))
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        # self.log_pin_usage(new_log_entry)
        self.log_pin_usage(new_log_entry, product_name, amount, pins_used_info)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()
        self.table.clearSelection()

        return f"{product_name}\n선택된 PIN {len(pins_to_use)}개로 {amount}원 사용이 완료되었습니다."

    # PIN 자동 사용 기능
    def use_pins_auto(self):
        if config['SETTING']['size_adjust'] == 'True':
            self.adjust_window_size()
            time.sleep(1)  # 창 크기 조절 후 잠시 대기
        # 현재 클립보드 데이터 저장
        original_clipboard = pyperclip.paste()
        total_used = 0
        new_log_entry = ""
        pins_used_info = []  # 통계 로그용 정보 수집
        try:
            # 1️⃣ HAOPLAY 창 핸들 찾기
            haoplay_hwnd = user32.FindWindowW(None, "HAOPLAY")
            if not haoplay_hwnd:
                # print("❌ HAOPLAY 창을 찾을 수 없습니다.")
                return "❌ HAOPLAY 창을 찾을 수 없습니다."

            # 2️⃣ "Chrome_WidgetWin_0" 컨트롤 핸들 찾기 (웹뷰 컨트롤)
            webview_hwnd = user32.FindWindowExW(haoplay_hwnd, 0, "Chrome_WidgetWin_0", None)
            if not webview_hwnd:
                # print("❌ 웹뷰 컨트롤을 찾을 수 없습니다.")
                return "❌ 웹뷰 컨트롤을 찾을 수 없습니다."

            # print(f"✅ 웹뷰 컨트롤 핸들 찾음: {webview_hwnd}")

            # 3️⃣ 창 활성화 (child_hWnd로 변경)
            user32.SetForegroundWindow(webview_hwnd)  # 웹뷰 컨트롤을 최상위로 활성화
            time.sleep(0.5)  # 안정성을 위해 대기
            
            pyautogui.hotkey('ctrl', 'shift', 'j')  # DevTools 열기
            time.sleep(1)
            pyautogui.hotkey('ctrl', '`') # Console 탭으로 이동
            time.sleep(0.2)

            # amount = int(self.find_amount())
            amount = self.find_amount()
            product_name = self.find_Product()
            new_log_entry += f'{product_name} - {amount}원\n'

            selected_pins = self.manager.find_pins_for_amount(amount)
            if not selected_pins:
                return "충분한 잔액이 없습니다."
            if len(selected_pins) == 0:
                return "사용할 수 있는 핀 조합이 없습니다."

            # 목록에서 최대 5개의 핀번호를 가져옴
            pins_to_inject = [selected_pins[i][0] for i in range(min(5, len(selected_pins)))]

            # 4️⃣ 핀번호를 입력박스에 추가
            self.add_pin_input_box(len(pins_to_inject))

            # 5️⃣ 핀번호들 자바스크립트를 통해 입력
            self.inject_pin_codes(pins_to_inject)

            # 모두 동의
            self.click_all_agree()

            # 제출
            if config['SETTING']['auto_submit'] == 'True':
                self.submit()
            # self.submit()

        except Exception as e:
            return f"❌ 자동 입력에 실패했습니다.\n{e}"

        finally:
            # 클립보드 데이터 원래 값으로 복원
            pyperclip.copy(original_clipboard)
            # print("✅ 클립보드 복원 완료.")

        # 사용한 핀의 잔액을 갱신하고 사용한 핀을 삭제
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            pins_used_info.append((pin, balance, used_amount, remaining_balance))
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        # self.log_pin_usage(new_log_entry)
        self.log_pin_usage(new_log_entry, product_name, amount, pins_used_info)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()

        return f"{product_name}\nPIN {len(selected_pins)}개 {amount}원 사용이 완료되었습니다."
    
    def use_pins_browser(self, amount):
        selected_pins = self.manager.find_pins_for_amount(amount)
        if not selected_pins:
            return "충분한 잔액이 없습니다."
        if len(selected_pins) == 0:
            return "사용할 수 있는 핀 조합이 없습니다."
        
        QMessageBox.information(self, "준비", f"{amount}원을 사용하기 위해 {len(selected_pins)}개의 PIN을 사용합니다.")
        if len(selected_pins) > 1:
            QMessageBox.information(self, "준비", f"핀 입력창을 {len(selected_pins)-1}개 추가해 주세요.")
        QMessageBox.information(self, "준비", "첫번째 핀 입력창의 첫번째 칸을 클릭하고 PIN이 입력될 준비를 하세요.\n3초 후 시작합니다.")
        time.sleep(3)
        total_used = 0
        new_log_entry = '브라우저 자동사용 - ' + str(amount) + '원\n'
        pins_used_info = []  # 통계 로그용 정보 수집
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            pyautogui.write(pin.replace("-", ""))  # PIN 입력
            used_amount = min(balance, amount - total_used)
            remaining_balance = balance - used_amount
            # 사용한 PIN 정보를 로그에 기록
            new_log_entry += f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {pin} [원금: {balance}] [사용된 금액: {used_amount}] [남은 잔액: {remaining_balance}]\n"
            pins_used_info.append((pin, balance, used_amount, remaining_balance))
            if remaining_balance > 0:
                self.manager.pins[pin] = remaining_balance
                total_used = amount
            else:
                del self.manager.pins[pin]
                total_used += balance

        # self.log_pin_usage(new_log_entry)
        self.log_pin_usage(new_log_entry, "브라우저 자동사용", amount, pins_used_info)
        self.manager.save_pins()
        self.manager.save_pins_to_txt()

        return f"PIN {len(selected_pins)}개 {amount}원 사용이 완료되었습니다."
    
    # PIN 사용 로그를 파일에 기록하는 기능
    def log_pin_usage(self, new_log_entry, product_name=None, total_amount=0, pins_used_info=None):
        if pins_used_info is None:
            pins_used_info = []
        
        try:
            # 기존 로그 파일 저장 및 구조화된 로그 추가
            with open("pin_usage_log.txt", "w", encoding='utf-8') as log_file:
                log_file.write(new_log_entry)
            
            # 통계용 로그 저장 (product_name과 total_amount가 있을 때만)
            if product_name and total_amount > 0 and pins_used_info:
                self.manager.add_stats_log_entry(
                    datetime.now().strftime('%Y-%m-%d'),
                    product_name,
                    total_amount,
                    pins_used_info
                )
            
            return True
        except Exception as e:
            self.show_warning_with_copy("로그 저장 오류", f"로그를 저장하는 중 오류가 발생했습니다: {str(e)}")
            return False

    def find_amount(self):
        javascript_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[2]/dd/strong', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);'''
        self.paste_javascript_code(javascript_code)
        time.sleep(0.2)

        # 클립보드에서 금액 가져오기 (pyperclip 사용)
        amount_text = pyperclip.paste()

        # 디버깅을 위한 출력
        # print(f"클립보드에서 가져온 텍스트: '{amount_text}'")
        
        try:
            # 쉼표와 공백 제거
            amount_text = amount_text.replace(" ", "").replace(",", "")
            
            # 숫자만 추출 (텍스트에서 '원' 등의 단위가 포함될 경우)
            amount_text = re.sub(r'[^\d]', '', amount_text)
            
            # 정수로 변환
            return int(amount_text)
        except ValueError as e:
            # 변환 실패 시 예외 처리
            QMessageBox.warning(self, "금액 감지 실패", f"금액을 가져오는데 실패했습니다.\n{amount_text}\n수동으로 금액을 입력해주세요.")
            amount, ok = QInputDialog.getInt(self, "금액 수동 입력", "사용할 금액:", 0, 0, 1000000, 1000)
            if ok:
                return amount
            else:
                raise ValueError("금액 입력이 취소되었습니다.")
    
    def find_Product(self):
        javascript_code = '''copy(document.evaluate('//*[@id="header"]/div/dl[1]/dd', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.innerText);
'''
        self.paste_javascript_code(javascript_code)
        time.sleep(0.2)
        name = pyperclip.paste()
        if not name:
            return "알 수 없는 상품"
        return name
    
    # 핀을 입력할 박스를 추가하는 기능
    def add_pin_input_box(self, num):
        if num < 1:
            return "사용되는 핀이 없습니다."

        # 5️⃣ 자바스크립트 코드 준비
        javascript_code = f'''
            while(document.querySelector("input[name='pyo_cnt']").value < {num})
                PinBoxInsert('pyo_cnt');
        '''
        self.paste_javascript_code(javascript_code)
    
    # javascript 코드를 붙여넣는 기능
    def inject_pin_codes(self, pins: list[str]):
        if pins is None or len(pins) == 0:
            return "사용되는 핀이 없습니다."

        arr = [item for pin in pins for item in pin.split("-")]
        arr_text = f"['{"', '".join(arr)}']"
        # 5️⃣ 자바스크립트 코드 준비
        javascript_code = '''
            let i = 0;
            arr = arr_text;
            document.querySelectorAll("#pinno").forEach(obj => {
                obj.querySelectorAll("input").forEach(input => {
                    input.value = arr[i++];
                })
            })
        '''.replace("arr_text", arr_text)
        self.paste_javascript_code(javascript_code)
    
    # javascript 코드를 붙여넣는 기능
    def paste_javascript_code(self, javascript_code):
        # 6️⃣ 클립보드에 자바스크립트 코드 복사 (pyperclip 사용)
        pyperclip.copy(javascript_code)
        # print(f"✅ 자바스크립트 코드 클립보드에 복사 완료.\n{pyperclip.paste()}")

        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)

        # 8️⃣ Enter 키 입력 (자바스크립트 실행)
        pyautogui.press('enter')
        time.sleep(0.1)

        # print("✅ 자바스크립트 실행 완료.")

    def click_all_agree(self):
        javascript_code = 'document.querySelector("#all-agree").click()'
        self.paste_javascript_code(javascript_code)


    def submit(self):
        javascript_code = 'goSubmit(document.form)'
        self.paste_javascript_code(javascript_code)

    def adjust_window_size(self, window_title=None, browser_name=None):
        """
        브라우저 창 크기를 작업 표시줄과 겹치지 않게 조절합니다.
        
        Args:
            window_title (str, optional): 창 제목. 제공되면 해당 제목의 창을 찾습니다.
            browser_name (str, optional): 브라우저 이름. 'chrome', 'edge', 'firefox' 중 하나.
        
        Returns:
            bool: 창 크기 조절 성공 여부
        """
        try:
            # 작업 표시줄 정보 가져오기
            taskbar_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if not taskbar_hwnd:
                self.show_warning_with_copy("오류", "작업 표시줄을 찾을 수 없습니다.")
                return False
                
            # 작업 표시줄 위치 및 크기 가져오기
            taskbar_rect = win32gui.GetWindowRect(taskbar_hwnd)
            
            # 화면 크기 가져오기
            screen_width = GetSystemMetrics(0)   # 화면 너비
            screen_height = GetSystemMetrics(1)  # 화면 높이
            
            # 작업 표시줄 위치 확인 (위, 아래, 왼쪽, 오른쪽)
            taskbar_pos = 'bottom'  # 기본값
            
            # 작업 표시줄 위치 판단
            if taskbar_rect[0] > 0:  # 왼쪽 가장자리가 0보다 크면 오른쪽이나 가운데
                if taskbar_rect[1] > 0:  # 위쪽 가장자리가 0보다 크면 아래쪽이나 가운데
                    if taskbar_rect[2] < screen_width:  # 오른쪽 가장자리가 화면 너비보다 작으면 왼쪽
                        taskbar_pos = 'left'
                    else:  # 그 외의 경우 오른쪽
                        taskbar_pos = 'right'
                else:  # 위쪽 가장자리가 0이면 위쪽
                    taskbar_pos = 'top'
            
            # 검색할 창
            window_found = False
            hwnd = None
            
            # HAOPLAY 검색 (기본값)
            haoplay_hwnd = win32gui.FindWindow(None, "HAOPLAY")
            if haoplay_hwnd:
                hwnd = haoplay_hwnd
                window_found = True
                
            if not window_found or not hwnd:
                self.show_warning_with_copy("오류", "조절할 창을 찾을 수 없습니다.")
                return False
            
            # 창이 최소화되어 있으면 복원
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # 새 창 위치 및 크기 계산
            current_rect = win32gui.GetWindowRect(hwnd)
            current_x, current_y, current_right, current_bottom = current_rect
            current_width = current_right - current_x
            print(f"현재 창 크기: {current_width}x{current_bottom - current_y}")
            
            # 새 창 위치 및 크기 계산 - 가로 크기는 유지
            new_x = 0  # 기본값으로 왼쪽 가장자리 사용
            new_y = 0  # 기본값으로 위쪽 가장자리 사용
            new_width = current_width # 현재 가로 크기 유지
            new_height = screen_height  # 기본값으로 화면 높이 사용

            if current_width > screen_width // 2:
                # 가로 크기가 너무 크면 조정
                new_width = screen_width // 2
                # new_x = (screen_width - new_width) // 2
            
            taskbar_height = taskbar_rect[3] - taskbar_rect[1]
            taskbar_width = taskbar_rect[2] - taskbar_rect[0]
            
            # 작업 표시줄 위치에 따라 창 높이만 조절
            if taskbar_pos == 'bottom':
                new_height = screen_height - taskbar_height
            elif taskbar_pos == 'top':
                new_y = taskbar_height
                new_height = screen_height - taskbar_height
            elif taskbar_pos == 'left' or taskbar_pos == 'right':
                # 좌/우 작업 표시줄의 경우 높이만 조절
                new_height = screen_height
            
            # 창 크기 및 위치 설정
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, new_x, new_y, new_width, new_height, win32con.SWP_SHOWWINDOW)
            
            # 창 활성화
            win32gui.SetForegroundWindow(hwnd)
            
            return True
            
        except Exception as e:
            self.show_warning_with_copy("오류", f"창 크기 조절 중 오류가 발생했습니다: {str(e)}")
            return False


if __name__ == "__main__":
    config_read()
    app = QApplication(sys.argv)
    ex = PinManagerApp()
    ex.show()
    sys.exit(app.exec())
