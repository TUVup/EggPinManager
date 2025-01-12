# EggPinManager
![image](https://github.com/user-attachments/assets/cf72bbf9-1664-4966-95dd-f6b4ecc720af)




**EggManager**는 에그머니의 PIN과 잔액을 손쉽게 관리할 수 있는 Python 기반의 도구입니다. PIN 추가, 삭제, 잔액 갱신, 목록 조회, 총 잔액 확인 등 PIN 관리에 필요한 다양한 기능을 제공합니다. 또한 특정 금액에 맞는 PIN을 자동으로 선택하여 사용할 수 있도록 도와줍니다. 현제 인게임 결제창에서만 작동합니다.(v1.0.3)

*업데이트 하는 방법: exe파일만 교체해 주세요.
## 주요 기능
- **PIN 추가 및 삭제**: 새로운 PIN을 등록하거나 기존 PIN을 삭제할 수 있습니다.
- **목록 조회 및 총 잔액 계산**: 모든 PIN과 해당 잔액을 출력하고 전체 잔액을 계산합니다.
- **금액에 맞는 PIN 자동 선택**: 특정 금액에 맞는 PIN을 자동으로 선택하고 입력할 수 있도록 지원합니다.
- **자동 입력 기능**: 선택한 PIN을 자동으로 브라우저에 입력할 수 있습니다.
- **우클릭 메뉴**: 우클릭 메뉴로 쉽게 관리할 수 있습니다.

  주기적으로 pins.txt를 백업해 주세요.
## 사용 방법
1. 프로그램 실행 후 다양한 옵션을 선택하여 PIN 관리 작업을 수행할 수 있습니다.
2. 옵션:
   - `PIN 추가`: 새로운 PIN을 추가합니다.
   - `PIN 삭제`: 기존 PIN을 삭제합니다.
   - `PIN 자동 사용`: 특정 금액에 맞는 PIN을 선택하고 자동 입력을 시작합니다.
   - `종료`: 프로그램을 종료합니다.
  
3. 우클릭 메뉴
   - `PIN 추가`: 새로운 PIN을 추가합니다.
   - `잔액 수정`: 잔액을 수정합니다.
   - `PIN 삭제`: 기존 PIN을 삭제합니다.
     
4. 자동 사용

   1. 핀 입력창에 제일 첫번째 칸을 클릭하고 기다리면 자동으로 핀 번호를 입력합니다.
   2. 여러개의 핀을 입력해야 할 때 팝업 메시지에 따라 진행합니다.
   3. 입력이 완료된 후 자동으로 마지막 핀에 잔액을 업데이트 합니다.
   4. 사용된 핀은 자동으로 삭제됩니다.
  
   자동 사용시 복사 붙여넣기가 되지 않으면 ctrl+shitf+j를 눌러 콘솔창을 띄운뒤 allow pasting 을 입력하고 엔터를 누르면 붙여넣기가 가능해집니다.

## 파일 관리
- **pins.json**: PIN과 잔액 정보를 저장하는 파일입니다.
- **pins.txt**: PIN과 잔액을 텍스트 형태로 출력하는 파일입니다.
- **pin_usage_log.txt**: 직전의 PIN 사용내역을 로그로 남깁니다.

## 설치 및 실행
1. [최신 버전 다운로드(v1.0.3)](https://github.com/TUVup/EggPinManager/releases/download/v1.0.3/EggManager_1.0.3.zip)
2. 압축을 풀고 실행.

## 빌드 정보

종속성 설치
- ```
  pip install pyinstaller pyautogui pyqt5
  ```

실행파일 빌드
- ```
  pyinstaller -w -F EggManager_GUI.py
  ```
