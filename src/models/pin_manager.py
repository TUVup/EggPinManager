"""
PIN 관리를 위한 핵심 클래스
PIN의 추가, 삭제, 수정 및 저장 기능 제공
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple
from itertools import combinations


class PinManager:
    """PIN 관리를 위한 클래스"""
    
    def __init__(self, config: dict):
        """
        PinManager 초기화
        
        Args:
            config (dict): 설정 정보를 담은 딕셔너리
        """
        self.filename = config["DEFAULT"]['pin_file']
        self.txt_filename = config["DEFAULT"]['txt_file']
        self.log_filename = config["DEFAULT"]['log_file']
        self.pins: Dict[str, int] = self.load_pins()

    def load_pins(self) -> dict:
        """
        JSON 파일에서 PIN 정보를 로드
        
        Returns:
            dict: PIN과 잔액 정보를 담은 딕셔너리
        """
        try:
            with open(self.filename, "r", encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_pins(self) -> None:
        """PIN 정보를 JSON 파일에 저장"""
        with open(self.filename, "w", encoding='utf-8') as file:
            json.dump(self.pins, file, indent=4)
    
    def save_pins_to_txt(self) -> None:
        """PIN 정보를 텍스트 파일에 저장"""
        with open(self.txt_filename, "w", encoding='utf-8') as file:
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                file.write(f"{idx}. {pin}: {balance}\n")

    def show_log(self) -> str:
        """
        로그 파일의 내용을 반환
        
        Returns:
            str: 로그 파일 내용 또는 에러 메시지
        """
        try:
            with open(self.log_filename, "r", encoding='utf-8') as log_file:
                return log_file.read()
        except FileNotFoundError:
            return "로그 파일을 찾을 수 없습니다."
        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def load_pins_from_log(self) -> str:
        """
        로그 파일에서 PIN 정보를 복구
        
        Returns:
            str: 복구 결과 메시지
        """
        try:
            with open(self.log_filename, "r", encoding='utf-8') as log_file:
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

    def add_pin(self, pin: str, balance: int) -> str:
        """
        새로운 PIN 추가
        
        Args:
            pin (str): PIN 번호
            balance (int): 잔액
            
        Returns:
            str: 추가 결과 메시지
        """
        self.pins[pin] = balance
        self.save_pins()
        self.save_pins_to_txt()
        return f"PIN {pin} 추가 완료. 잔액: {balance}"

    @staticmethod
    def format_pin(pin: str) -> str:
        """
        PIN 형식 포맷팅
        
        Args:
            pin (str): 포맷팅할 PIN
            
        Returns:
            str: 포맷팅된 PIN
        """
        if len(pin) == 20 and pin.isdigit():
            return f"{pin[:5]}-{pin[5:10]}-{pin[10:15]}-{pin[15:]}"
        return pin

    @staticmethod
    def unformat_pin(formatted_pin: str) -> str:
        """
        PIN 형식에서 하이픈 제거
        
        Args:
            formatted_pin (str): 포맷팅된 PIN
            
        Returns:
            str: 하이픈이 제거된 PIN
        """
        return formatted_pin.replace("-", "")

    @staticmethod
    def is_valid_pin_format(pin: str) -> bool:
        """
        PIN 형식 유효성 검사
        
        Args:
            pin (str): 검사할 PIN
            
        Returns:
            bool: 유효한 PIN 형식이면 True
        """
        pattern = re.compile(r'^\d{5}-\d{5}-\d{5}-\d{5}$')
        return bool(pattern.match(pin))

    def delete_pin(self, pin: str) -> str:
        """
        PIN 삭제
        
        Args:
            pin (str): 삭제할 PIN
            
        Returns:
            str: 삭제 결과 메시지
        """
        pin = self.format_pin(pin)
        if pin in self.pins:
            del self.pins[pin]
            self.save_pins()
            self.save_pins_to_txt()
            return f"PIN {pin} 삭제 완료."
        return f"PIN {pin}은(는) 존재하지 않습니다."

    def update_pin_balance(self, pin: str, new_balance: int) -> bool:
        """
        PIN 잔액 업데이트
        
        Args:
            pin (str): 업데이트할 PIN
            new_balance (int): 새로운 잔액
            
        Returns:
            bool: 업데이트 성공 여부
        """
        if pin in self.pins:
            self.pins[pin] = new_balance
            self.save_pins()
            self.save_pins_to_txt()
            return True
        return False

    def get_total_balance(self) -> int:
        """
        전체 잔액 합계 반환
        
        Returns:
            int: 전체 잔액 합계
        """
        return sum(self.pins.values())

    def list_pins(self) -> List[Tuple[str, int]]:
        """
        PIN 목록 반환
        
        Returns:
            List[Tuple[str, int]]: (PIN, 잔액) 튜플의 리스트
        """
        return list(self.pins.items())

    def find_pins_for_amount(self, amount: int) -> List[Tuple[str, int]]:
        """
        지정된 금액에 맞는 최적의 PIN 조합 찾기
        
        Args:
            amount (int): 필요한 금액
            
        Returns:
            List[Tuple[str, int]]: 선택된 (PIN, 잔액) 튜플의 리스트
        """
        sorted_pins = sorted(self.pins.items(), key=lambda x: x[1])
        selected_pins = []
        total_selected = 0
        best_combination = []
        best_total = 0

        for pin, balance in sorted_pins:
            if total_selected >= amount:
                break
            selected_pins.append((pin, balance))
            total_selected += balance

        if total_selected >= amount and len(selected_pins) <= 5:
            return selected_pins
        else:
            for r in range(1, 6):
                for combination in combinations(sorted_pins, r):
                    total = sum(balance for pin, balance in combination)
                    if total >= amount and (best_total == 0 or total < best_total):
                        best_combination = combination
                        best_total = total

            if best_total >= amount:
                return best_combination

        return []

    def pin_check(self, pin: str) -> bool:
        """
        PIN 존재 여부 확인
        
        Args:
            pin (str): 확인할 PIN
            
        Returns:
            bool: PIN이 존재하면 True
        """
        pin = self.format_pin(pin)
        return pin in self.pins

    def log_pin_usage(self, log_entry: str) -> None:
        """
        PIN 사용 내역을 로그 파일에 기록
        
        Args:
            log_entry (str): 기록할 로그 내용
        """
        with open(self.log_filename, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {log_entry}\n") 