"""
GUI 스타일 정의
테마 및 스타일시트 관리
"""

class Styles:
    """애플리케이션 스타일 정의"""

    @staticmethod
    def get_theme(theme: str = "light", font_size: int = 9) -> str:
        """
        테마에 따른 스타일시트 반환
        
        Args:
            theme (str): 테마 이름 ("light" 또는 "dark")
            font_size (int): 폰트 크기
            
        Returns:
            str: QSS 스타일시트
        """
        # 기본 폰트 설정
        base_style = f"""
            QWidget {{
                font-family: "맑은 고딕", Arial;
                font-size: {font_size}pt;
            }}
        """

        if theme == "dark":
            return base_style + """
                QMainWindow, QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3b3b3b;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #4b4b4b;
                }
                QPushButton:pressed {
                    background-color: #2b2b2b;
                }
                QLineEdit {
                    background-color: #3b3b3b;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #3b3b3b;
                    alternate-background-color: #333333;
                    border: 1px solid #555555;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #555555;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QMenu::item:selected {
                    background-color: #3b3b3b;
                }
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
            """
        else:  # light theme
            return base_style + """
                QMainWindow, QDialog {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QWidget {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #b0b0b0;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #b0b0b0;
                    padding: 5px;
                    border-radius: 3px;
                }
                QTableWidget {
                    background-color: #ffffff;
                    alternate-background-color: #f5f5f5;
                    border: 1px solid #b0b0b0;
                }
                QHeaderView::section {
                    background-color: #e0e0e0;
                    padding: 5px;
                    border: 1px solid #b0b0b0;
                }
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #b0b0b0;
                }
                QMenu::item:selected {
                    background-color: #e0e0e0;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                }
            """