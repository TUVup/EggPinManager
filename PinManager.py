import json
import pyautogui
import time

class PinManager:
    def __init__(self, filename="pins.json", txt_filename="pins.txt"):
        self.filename = filename
        self.txt_filename = txt_filename
        self.pins = self.load_pins()
        self.last_used_pin = None

    def load_pins(self):
        try:
            with open(self.filename, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_pins(self):
        with open(self.filename, "w") as file:
            json.dump(self.pins, file, indent=4)
        self.save_pins_to_txt()

    def save_pins_to_txt(self):
        with open(self.txt_filename, "w") as file:
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                file.write(f"{idx}. {pin}: {balance}\n")

    def add_pin(self, pin, balance):
        if pin in self.pins:
            print(f"PIN {pin}은(는) 이미 존재합니다.")
        else:
            self.pins[pin] = balance
            self.save_pins()
            print(f"PIN {pin} 추가 완료. 잔액: {balance}")

    def delete_pin(self, pin):
        if pin in self.pins:
            del self.pins[pin]
            self.save_pins()
            print(f"PIN {pin} 삭제 완료.")
        else:
            print(f"PIN {pin}은(는) 존재하지 않습니다.")

    def update_balance(self, pin, amount):
        if pin in self.pins:
            lastbal = self.pins[pin]
            self.pins[pin] = amount
            if self.pins[pin] <= 0:
                print("0이하의 금액은 불가능합니다.")
            else:
                self.save_pins()
                print(f"PIN {pin} 잔액 갱신 완료. 이전 잔액: {lastbal} 현재 잔액: {self.pins[pin]}")
        else:
            print(f"PIN {pin}은(는) 존재하지 않습니다.")

    def get_total_balance(self):
        self.list_pins()
        total_balance = sum(self.pins.values())
        print(f"총 잔액: {total_balance}")
        return total_balance

    def list_pins(self):
        if not self.pins:
            print("등록된 PIN이 없습니다.")
        else:
            print("현재 등록된 PIN 목록:")
            for idx, (pin, balance) in enumerate(self.pins.items(), start=1):
                print(f"{idx}. PIN: {pin}, 잔액: {balance}")

    def find_pins_for_amount(self, amount):
        sorted_pins = sorted(self.pins.items(), key=lambda x: x[1])
        selected_pins = []
        total_selected = 0

        for pin, balance in sorted_pins:
            if total_selected >= amount:
                break
            selected_pins.append((pin, balance))
            total_selected += balance

        if total_selected >= amount:
            print("선택된 PIN:")
            for pin, balance in selected_pins:
                print(f"PIN: {pin}, 잔액: {balance}")
            return selected_pins
        else:
            print("충분한 잔액이 없습니다.")
            return []

    def use_pins(self, amount):
        selected_pins = self.find_pins_for_amount(amount)

        if not selected_pins:
            print("해당 금액에 맞는 PIN을 사용할 수 없습니다.")
            return

        print("브라우저 창을 선택하고 PIN이 입력될 준비를 하세요. 4초 후 시작합니다.")

        total_used = 0
        for pin, balance in selected_pins:
            if total_used >= amount:
                break
            time.sleep(4)
            pyautogui.write(pin.replace("-", ""))  # PIN 입력 (하이픈 제거 후 붙여넣기)
            print(f"\nPIN {pin}이 입력되었습니다.")
            remaining_balance = balance - (amount - total_used)
            if remaining_balance > 0:
                self.pins[pin] = remaining_balance
                self.last_used_pin = (pin, remaining_balance)
                print(f"PIN {pin} 사용 완료. 남은 잔액: {remaining_balance}")
                total_used = amount
            else:
                self.delete_pin(pin)
                total_used += balance
                self.last_used_pin = (pin, 0)
                if total_used < amount:
                    print("\n추가를 눌러 다음 PIN을 입력할 준비를 하세요. 3초 후 진행됩니다.")
                    time.sleep(3)
                    print("브라우저 창을 선택하고 PIN이 입력될 준비를 하세요. 4초 후 시작합니다.")
            self.save_pins()

if __name__ == "__main__":
    manager = PinManager()

    while True:
        print("\n옵션: 추가(add), 삭제(delete), 잔액 수정(update), 총 잔액(total), 목록 보기(list), PIN 찾기(find), PIN 사용(use), 종료(quit)")
        option = input("옵션을 선택하세요: ").strip().lower()
        
        if option == "add":
            pin = input("PIN 입력 (형식: 12345-12345-12345-12345): ").strip()
            balance = float(input("잔액 입력: "))
            manager.add_pin(pin, balance)
        elif option == "delete":
            pin = input("삭제할 PIN 입력: ").strip()
            manager.delete_pin(pin)
        elif option == "update":
            pin = input("잔액을 수정할 PIN 입력: ").strip()
            amount = float(input("수정할 금액 입력: "))
            manager.update_balance(pin, amount)
        elif option == "total":
            manager.get_total_balance()
        elif option == "list":
            manager.list_pins()
        elif option == "find":
            amount = float(input("PIN을 찾을 금액 입력: "))
            manager.find_pins_for_amount(amount)
        elif option == "use":
            amount = float(input("사용할 금액 입력: "))
            manager.use_pins(amount)
        elif option == "quit":
            print("PinManager를 종료합니다.")
            break
        else:
            print("잘못된 옵션입니다. 다시 시도하세요.")
