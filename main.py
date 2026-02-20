# Import necessary modules for date/time handling, system operations, data manipulation, HTTP requests, currency symbols, threading, financial data, and GUI components.
import datetime as dt
from datetime import timedelta
import sys
import pandas as pd
import requests
from currency_symbols import CurrencySymbols
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QStackedWidget, QFrame, QComboBox, QScrollArea
from tkinter import messagebox, filedialog
from lightweight_charts.widgets import QtChart
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QDialog, QLineEdit, QDateEdit, QCompleter
from PyQt6.QtGui import QFont, QPixmap, QIcon, QFontDatabase, QPalette
from PyQt6.QtCore import Qt, QTimer
from urllib.request import urlopen

# Import custom screen classes for stock and search functionality.
from stock_screen import StockScreen    
from search_screen import SearchScreen

# Load environment variables from .env file
load_dotenv()

# Custom scroll area class that allows independent scrolling behavior.
class IndependentScrollArea(QScrollArea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow wheel events even when not focused for better UX.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        # Handle wheel events to enable scrolling only when necessary.
        delta_y = event.pixelDelta().y() if not event.pixelDelta().isNull() else event.angleDelta().y()
        sb = self.verticalScrollBar()
        if sb is None:
            return super().wheelEvent(event)
        at_top = sb.value() == sb.minimum()
        at_bottom = sb.value() == sb.maximum()
        if (delta_y > 0 and not at_top) or (delta_y < 0 and not at_bottom):
            super().wheelEvent(event)
            event.accept()
            return
        event.accept()

# Main application class for the Investmate portfolio management app.
class invest_mate(QMainWindow):
    """
    The main window class for the Investmate application, handling portfolio management,
    currency conversion, stock data fetching, and UI components.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Investmate")
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: #171B18; color: white; margin: 0px; padding: 0px;")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.showFullScreen()

        # Initialize settings and portfolio data attributes.
        self.selected_stock = []
        self.portfolio_holdings = []  # List of individual holdings.
        self.total_portfolio_holdings = []  # Grouped holdings for display.
        self.total_profit_loss = 0
        self.total_portfolio_value = 0
        self.total_profit_loss_percent = 0
        self.total_portfolio_change = 0
        self.daily_change = 0
        self.daily_change_percent = 0
        self.currency = "USD"
        self.currency_rate = 0  
        self.last_updated_currency_date = dt.datetime.now()
        # Predefined stock symbols for autocomplete.
        self.stock_autocomplete_values = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "FB", "BRK-A", "NVDA", "JPM", "JNJ", "V", "UNH", "HD", "PG", "DIS", "MA", "BAC", "XOM", "VZ", "ADBE"]
        # Input fields configuration for adding holdings.
        self.input_list = [{"name": "Symbol", "type": "text"}, {"name": "Purchase Price", "type": "number"}, {"name": "Fees", "type": "number"}, {"name": "Units", "type": "number"}, {"name": "Date Purchased (DD-MM-YYYY)", "type": "date"}]
        self.input_fields = []
        # UI labels for portfolio display.
        self.portfolio_value_label = QLabel(f"{CurrencySymbols.get_symbol(self.currency)}{self.convert_currency(self.total_portfolio_value):,.2f}")
        self.portfolio_value_label.setFont(QFont('Geist Mono', 32))
        self.currency_selector = QComboBox()
        self.currency_selector.addItems(["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY"])

    def update_currency(self):
        """
        Fetches the latest currency conversion rate from an external API and updates the currency_rate attribute.
        """
        try:
            fx_api_key = os.getenv('FX_RATES_API_KEY')
            response = requests.get(f"https://api.fxratesapi.com/latest?base=USD&currencies={self.currency}&resolution=1m&format=json&api_key={fx_api_key}")
            data = response.json()
            self.currency_rate = data['rates'][self.currency]
            self.currency_rate_last_updated = dt.datetime.now()
        except Exception as e:
            messagebox.showerror("Currency Conversion Error", f"Error fetching currency conversion rate: {e}")

    def convert_currency(self, amount):
        """
        Converts the given amount to the selected currency using the current rate.
        """
        if self.currency == "USD":
            return amount
        else:
            if (dt.datetime.now() - self.last_updated_currency_date).seconds > 600:
                self.update_currency()
            else:
                return amount * self.currency_rate

    def set_loading_cursor(self, loading: bool):
        """
        Sets the application-wide cursor to a wait cursor during long operations.
        """
        if loading:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def clear_stock_screen(self):
        """
        Clears and recreates the stock screen widget.
        """
        self.main_widget.removeWidget(self.stock_screen)
        self.stock_screen.deleteLater()
        self.stock_screen = StockScreen()
        self.main_widget.addWidget(self.stock_screen)
            
    def switch_tabs(self, tab_name):
        """
        Switches between different tabs (home, search, stocks) in the stacked widget.
        """
        if self.main_widget.currentIndex() == 0 and tab_name == "home":
            return
        elif self.main_widget.currentIndex() == 1 and tab_name == "search":
            return
        else:
            if tab_name == "home":
                self.main_widget.setCurrentIndex(0)
                self.home_button.setIcon(QIcon(QPixmap('images/home-active.png')))
                self.search_button.setIcon(QIcon(QPixmap('images/search-unactive.png')))
                self.clear_stock_screen()
            elif tab_name == "search":
                self.main_widget.setCurrentIndex(1)
                self.home_button.setIcon(QIcon(QPixmap('images/home-unactive.png')))
                self.search_button.setIcon(QIcon(QPixmap('images/search-active.png')))
                self.clear_stock_screen()
            else:
                self.main_widget.setCurrentIndex(2)
                self.home_button.setIcon(QIcon(QPixmap('images/home-unactive.png')))
                self.search_button.setIcon(QIcon(QPixmap('images/search-unactive.png')))

    def initalise_fonts(self):
        """
        Loads custom fonts for the application.
        """
        QFontDatabase.addApplicationFont("fonts/GeistMono-Light.ttf")
        QFontDatabase.addApplicationFont("fonts/GeistMono-Regular.ttf")
        QFontDatabase.addApplicationFont("fonts/GeistMono-Bold.ttf")

    def create_header(self):
        """
        Creates the header section with navigation buttons, logo, and clock.
        """
        header_widget = QWidget()
        header_widget.setFixedHeight(70)
        self.header_layout = QHBoxLayout()
        header_widget.setLayout(self.header_layout)
        header_widget.setStyleSheet("margin: 0px; padding: 0px;")
        self.main_layout.addWidget(header_widget)
        
        self.left_nav = QWidget()
        self.left_nav_layout = QHBoxLayout()
        self.left_nav.setLayout(self.left_nav_layout)
        self.right_nav = QWidget()
        self.right_nav_layout = QHBoxLayout()
        self.right_nav.setLayout(self.right_nav_layout)
        self.right_nav_left = QWidget()
        self.right_nav_left_layout = QHBoxLayout()
        self.right_nav_left.setLayout(self.right_nav_left_layout)
        self.right_nav_right = QWidget()
        self.right_nav_right_layout = QHBoxLayout()
        self.right_nav_right.setLayout(self.right_nav_right_layout)
        self.header_layout.addWidget(self.left_nav)
        self.logo = QLabel()
        pixmap = QPixmap('images/logo.png')
        self.logo.setPixmap(pixmap.scaled(200, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.left_nav_layout.addWidget(self.logo)
        self.left_nav_layout.addSpacing(100)
        self.time_label = QLabel("")
        self.time_label.setFont(QFont('Geist Mono', 15))
        self.left_nav_layout.addWidget(self.time_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_clock)
        self.timer.start(1000)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.right_nav)
        self.right_nav_layout.addWidget(self.right_nav_left)
        self.right_nav_layout.addWidget(self.right_nav_right)
        self.home_button = QPushButton()
        self.right_nav_left_layout.addWidget(self.home_button)
        home_pixmap = QPixmap('images/home-active.png') 
        home_icon = QIcon(home_pixmap)
        self.home_button.setIcon(home_icon)
        self.home_button.clicked.connect(lambda: self.switch_tabs("home"))
        self.home_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button = QPushButton()
        self.right_nav_left_layout.addWidget(self.search_button)
        search_pixmap = QPixmap('images/search-unactive.png') 
        search_icon = QIcon(search_pixmap)
        self.search_button.setIcon(search_icon)
        self.search_button.clicked.connect(lambda: self.switch_tabs("search"))
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_button = QPushButton()
        self.right_nav_right_layout.addWidget(self.profile_button)
        profile_pixmap = QPixmap('images/Profile.png') 
        profile_icon = QIcon(profile_pixmap)
        self.profile_button.setIcon(profile_icon)
        self.username_label = QLabel("John Doe")
        self.username_label.setFont(QFont('Inter', 15))
        self.right_nav_right_layout.addWidget(self.username_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: white; background-color: white;") 
        self.main_layout.addWidget(line)

    def create_screens(self):
        """
        Creates the main stacked widget for different screens (home, search, stock).
        """
        self.main_widget = QStackedWidget()
        self.main_layout.addWidget(self.main_widget)
        self.main_scroll_area = QScrollArea()
        self.main_scroll_area.setStyleSheet("border: none;")
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_widget.addWidget(self.main_scroll_area)
        self.search_screen = SearchScreen(self.switch_tabs, lambda stock: self.handle_trending_stock_click(stock))
        self.main_widget.addWidget(self.search_screen)
        self.stock_screen = StockScreen()
        self.main_widget.addWidget(self.stock_screen)

    def create_info_section(self):
        """
        Creates the info section displaying portfolio value, changes, and hot stocks.
        """
        self.main_scroll_area_container = QWidget()
        self.main_scroll_area_container.setStyleSheet("margin-top: 10px; padding: 20px;")
        self.main_scroll_area_layout = QVBoxLayout(self.main_scroll_area_container)
        self.main_scroll_area.setWidget(self.main_scroll_area_container)
        self.info = QWidget()
        self.info_layout = QHBoxLayout()
        self.info.setLayout(self.info_layout)
        self.main_scroll_area_layout.addWidget(self.info)
        self.info.setStyleSheet("padding: 10px;")
        self.create_info_left()
        self.create_info_right()

    def determine_color(self, value):
        """
        Determines the color (green, red, or grey) based on the value's sign.
        """
        if value > 0:
            return "#14AE5C"  # Green for positive
        elif value < 0:
            return "#F24822"  # Red for negative
        else:
            return "#9B9B9B"  # Grey for neutral
        
    def determine_icon(self, value, size=9):
        """
        Determines the icon (up, down, or none) based on the value's sign.
        """
        if value > 0:
            return QPixmap('images/up-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif value < 0:
            return QPixmap('images/down-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:    
            return QPixmap('')

    def create_info_left(self):
        """
        Creates the left part of the info section with portfolio value and changes.
        """
        self.info_left = QWidget()
        self.info_left_layout = QVBoxLayout()
        self.info_left.setLayout(self.info_left_layout)
        self.info_left.setStyleSheet("padding: 0px; margin: 0px;")
        self.info_layout.addWidget(self.info_left)
        self.info_left_layout.addWidget(self.portfolio_value_label)
        self.info_left_lower = QWidget()
        self.info_left_lower.setStyleSheet("padding: 0px; margin: 0px;")
        self.info_left_lower_layout = QHBoxLayout()
        self.info_left_lower.setLayout(self.info_left_lower_layout)
        self.info_left_layout.addWidget(self.info_left_lower)
        label_portfolio = QLabel("Portfolio Value")
        label_portfolio.setFont(QFont('Inter', 15, QFont.Weight.Light))
        label_portfolio.setStyleSheet("color: #9B9B9B;")
        self.info_left_lower_layout.addWidget(label_portfolio)
        self.info_left_lower_layout.addSpacing(10)
        self.portfolio_change_label = QLabel()
        self.portfolio_change_label.setPixmap(self.determine_icon(self.total_portfolio_change))
        self.info_left_lower_layout.addWidget(self.portfolio_change_label)
        self.info_left_lower_layout.addSpacing(1)
        self.portfolio_change_label_text = QLabel(f"{self.convert_currency(self.total_portfolio_change):.2f}%")
        self.portfolio_change_label_text.setFont(QFont('Roboto', 15, QFont.Weight.Light))
        self.portfolio_change_label_text.setStyleSheet(f"color: {self.determine_color(self.total_portfolio_change)};")
        self.info_left_lower_layout.addWidget(self.portfolio_change_label_text)
        self.info_left_lower_layout.addStretch(0)
        self.info_left_layout.addStretch(0)
        self.info_left_bottom = QWidget()
        self.info_left_bottom_layout = QHBoxLayout()
        self.info_left_bottom.setLayout(self.info_left_bottom_layout)
        self.info_left_layout.addWidget(self.info_left_bottom)
        self.info_left_bottom.setStyleSheet("padding: 0px; margin: 0px;")
        self.create_additional_info_data()

    def create_line_spacer(self, layout, height):
        """
        Creates a vertical line spacer for layout separation.
        """
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setFixedHeight(height)
        line.setStyleSheet("color: #777777; background-color: #777777; border-radius: 5px;")
        layout.addWidget(line)
    
    def create_additional_info_data(self):
        """
        Creates additional info data for daily change and P&L.
        """
        self.info_left_bottom_left = QWidget()
        self.info_left_bottom_left_layout = QVBoxLayout()
        self.info_left_bottom_left.setLayout(self.info_left_bottom_left_layout)
        self.info_left_bottom_left.setStyleSheet("padding: 0px; margin: 0px;")
        self.info_left_bottom_layout.addWidget(self.info_left_bottom_left)
        self.info_left_bottom_left_layout.addStretch(0)
        self.daily_change_label = QLabel(f"{CurrencySymbols.get_symbol(self.currency)}{self.convert_currency(self.daily_change):.2f}")
        self.daily_change_label.setFont(QFont('Geist Mono', 20))
        self.info_left_bottom_left_layout.addWidget(self.daily_change_label)
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet(" padding: 0px; margin: 0px;")   
        bottom_layout = QHBoxLayout()
        bottom_widget.setLayout(bottom_layout)
        self.info_left_bottom_left_layout.addWidget(bottom_widget)
        label_daily_change = QLabel("Daily Change")
        label_daily_change.setFont(QFont('Inter', 15, QFont.Weight.Light))
        label_daily_change.setStyleSheet("color: #9B9B9B;")
        bottom_layout.addWidget(label_daily_change)
        bottom_layout.addSpacing(7)
        self.daily_change_icon = QLabel()
        daily_change_pixmap = QPixmap(self.determine_icon(self.daily_change_percent))
        self.daily_change_icon.setPixmap(daily_change_pixmap)
        bottom_layout.addWidget(self.daily_change_icon)
        bottom_layout.addSpacing(1)
        self.daily_change_label_text = QLabel(f"{self.daily_change_percent:.2f}%")
        self.daily_change_label_text.setFont(QFont('Roboto', 15, QFont.Weight.Light))
        self.daily_change_label_text.setStyleSheet(f"color: {self.determine_color(self.daily_change_percent)};")
        bottom_layout.addWidget(self.daily_change_label_text)
        bottom_layout.addStretch(0)
        self.info_left_bottom_left_layout.addStretch(0)
        self.create_line_spacer(self.info_left_bottom_layout, 100)
        self.info_left_bottom_right = QWidget()
        self.info_left_bottom_right_layout = QVBoxLayout()
        self.info_left_bottom_right.setLayout(self.info_left_bottom_right_layout)
        self.info_left_bottom_right.setStyleSheet("  padding: 0px; margin: 0px;")
        self.info_left_bottom_layout.addWidget(self.info_left_bottom_right)
        self.info_left_bottom_right_layout.addStretch(0)
        self.profit_loss_label = QLabel(f"{CurrencySymbols.get_symbol(self.currency)}{self.total_profit_loss:.2f}")
        self.profit_loss_label.setFont(QFont('Geist Mono', 20))
        self.info_left_bottom_right_layout.addWidget(self.profit_loss_label)
        bottom_widget_right = QWidget()
        bottom_widget_right.setStyleSheet("  padding: 0px; margin: 0px;")   
        bottom_layout_right = QHBoxLayout()
        bottom_widget_right.setLayout(bottom_layout_right)
        self.info_left_bottom_right_layout.addWidget(bottom_widget_right)
        label_profit_loss = QLabel("P&L")
        label_profit_loss.setFont(QFont('Inter', 15, QFont.Weight.Light))
        label_profit_loss.setStyleSheet("color: #9B9B9B;")
        bottom_layout_right.addWidget(label_profit_loss)
        bottom_layout_right.addSpacing(7)
        self.profit_loss_icon = QLabel()
        profit_loss_pixmap = QPixmap(self.determine_icon(self.total_profit_loss_percent))
        self.profit_loss_icon.setPixmap(profit_loss_pixmap)
        bottom_layout_right.addWidget(self.profit_loss_icon)
        bottom_layout_right.addSpacing(1)
        self.profit_loss_label_text = QLabel(f"{self.total_profit_loss_percent:.2f}%")
        self.profit_loss_label_text.setFont(QFont('Roboto', 15, QFont.Weight.Light))
        self.profit_loss_label_text.setStyleSheet(f"color: {self.determine_color(self.total_profit_loss_percent)};")
        bottom_layout_right.addWidget(self.profit_loss_label_text)
        bottom_layout_right.addStretch(0)
        self.info_left_bottom_right_layout.addStretch(0)
        self.info_left_bottom_left_layout.setContentsMargins(0, 0, 0, 0)
        self.info_left_bottom_right_layout.setContentsMargins(20, 0, 0, 0)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.info_left_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout_right.setContentsMargins(0, 0, 0, 0)
        self.info_left_bottom_layout.setStretch(0, 1)
        self.info_left_bottom_layout.setStretch(1, 0)
        self.info_left_bottom_layout.setStretch(2, 1)
    
    def get_trending_stocks(self):
        """
        Fetches trending stocks data from an API.
        """
        stock_list = []
        fmp_api_key = os.getenv('FINANCIAL_MODELING_PREP_API_KEY')
        data = requests.get(f"https://financialmodelingprep.com/stable/biggest-gainers?apikey={fmp_api_key}").json()
        for stock in data:
            if "Inc." in stock["name"]:
                stock_list.append(stock)
            if len(stock_list) >= 3:
                break
        return stock_list

    def create_info_right(self):
        """
        Creates the right part of the info section with hot stocks.
        """
        self.info_right = QWidget()
        self.info_right.setStyleSheet("padding: 0px; margin: 0px;")
        self.info_right_layout = QVBoxLayout()
        self.info_right.setLayout(self.info_right_layout)
        self.info_layout.addWidget(self.info_right)
        self.info_layout.setStretch(1, 5)
        self.info_layout.setStretch(0, 3)
        hot_stocks_label = QLabel("Hot Stocks")
        hot_stocks_label.setStyleSheet("color: #9B9B9B;")
        hot_stocks_label.setFont(QFont('Inter', 20, QFont.Weight.Light))
        self.info_right_layout.addWidget(hot_stocks_label)
        self.info_right_buttons = QWidget()
        self.info_right_button_layout = QHBoxLayout()
        self.info_right_buttons.setLayout(self.info_right_button_layout)
        self.info_right_layout.addWidget(self.info_right_buttons)
        data = self.get_trending_stocks()
        for asset in data:

            stock_rectangle = QWidget()
            stock_rectangle_layout = QHBoxLayout()
            stock_rectangle.setStyleSheet("background-color: #262626; border-radius: 4px;")
            stock_rectangle.setFixedHeight(150)
            stock_rectangle.setLayout(stock_rectangle_layout)
            self.info_right_button_layout.addWidget(stock_rectangle)
            company_logo_widget = QWidget()
            company_logo_layout = QVBoxLayout()
            company_logo_widget.setLayout(company_logo_layout)
            stock_rectangle_layout.addWidget(company_logo_widget)
            logo_token = os.getenv('LOGO_DEV_TOKEN')
            logo = requests.get(f"https://img.logo.dev/ticker/{asset['symbol']}?token={logo_token}&size=64&retina=true")
            logo_image = QPixmap()
            logo_image.loadFromData(logo.content)
            logo_image = logo_image.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            company_logo = QLabel()
            company_logo.setPixmap(logo_image)
            company_logo_layout.addWidget(company_logo)
            company_logo_layout.addStretch(0)
            company_info = QWidget()
            company_info_layout = QVBoxLayout()
            company_info.setLayout(company_info_layout)
            stock_rectangle_layout.addWidget(company_info)
            company_info_name_section = QWidget()
            company_info_name_section_layout = QHBoxLayout()
            company_info_name_section.setLayout(company_info_name_section_layout)
            company_info_layout.addWidget(company_info_name_section)
            company_name = QLabel(f"{asset['name']}")
            company_name.setFont(QFont('Inter', 12))
            company_info_name_section_layout.addWidget(company_name)
            ticker_label = QLabel(f"${asset['symbol']}")
            ticker_label.setStyleSheet("color: #9B9B9B;")
            ticker_label.setFont(QFont('Inter', 8, QFont.Weight.Light))
            company_info_name_section_layout.addWidget(ticker_label)
            company_info_name_section_layout.addStretch(0)
            company_prices = QWidget()
            company_prices_layout = QHBoxLayout()
            company_prices.setLayout(company_prices_layout)
            company_info_layout.addWidget(company_prices)
            stock_price_label = QLabel(f"{CurrencySymbols.get_symbol(self.currency)}{self.convert_currency(asset['price']):.2f}")
            stock_price_label.setFont(QFont('Geist Mono', 12, QFont.Weight.Light))
            company_prices_layout.addWidget(stock_price_label)
            stock_change_icon = QLabel()
            stock_change_pixmap = QPixmap(self.determine_icon(asset['change'], size=10))
            stock_change_icon.setPixmap(stock_change_pixmap)
            company_prices_layout.addWidget(stock_change_icon)
            stock_change_label = QLabel(f"{asset['change']:.2f}%")
            stock_change_label.setStyleSheet(f"color: {self.determine_color(asset['change'])};")
            stock_change_label.setFont(QFont('Roboto', 10, QFont.Weight.Light))
            company_prices_layout.addWidget(stock_change_label)
            company_prices_layout.addStretch(0)
            company_info_layout.addStretch(0)
            see_more_button = QPushButton("See More")
            # Fix lambda closure: use default argument to capture current asset
            see_more_button.clicked.connect(lambda checked=False, stock=asset['symbol']: self.handle_trending_stock_click(stock))
            see_more_button.setStyleSheet("""
                QPushButton {
                    background-color: #0062FF; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                    height: 25px;
                    padding: 5px;
                    font-family: 'Inter';
                    font-size: 11pt;
                    font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
            see_more_button.setFixedWidth(200)
            see_more_button.setCursor(Qt.CursorShape.PointingHandCursor)
            company_info_layout.addWidget(see_more_button)
            stock_rectangle_layout.setContentsMargins(10, 10, 10, 10)
            company_info_name_section_layout.setContentsMargins(0, 0, 0, 0)
            company_prices_layout.setContentsMargins(0, 0, 0, 0)
            company_info_layout.setContentsMargins(0, 10, 10, 10)
        self.info_right_layout.addStretch(0)

    def handle_trending_stock_click(self, stock):
        """
        Handles click on a trending stock to switch to stock screen.
        """
        self.set_loading_cursor(True)
        units = 0
        for holding in self.portfolio_holdings:
            if holding[0] == stock:
                units += int(holding[3])
        self.set_selected_stock([stock, units])
        self.switch_tabs("stocks")
        self.set_loading_cursor(False)

    def create_portfolio_section(self):
        """
        Creates the portfolio section with assets and chart.
        """
        self.portfolio_section = QWidget()
        self.portfolio_section_layout = QHBoxLayout()
        self.portfolio_section.setLayout(self.portfolio_section_layout)
        self.main_scroll_area_layout.addWidget(self.portfolio_section)
        self.create_portfolio_section_left()
        self.create_line_spacer(self.portfolio_section_layout, 550)
        self.create_portfolio_section_right()
        self.portfolio_section_layout.setStretch(0, 1)
        self.portfolio_section_layout.setStretch(1, 0)
        self.portfolio_section_layout.setStretch(2, 1)
        self.portfolio_section_layout.setContentsMargins(20, 0, 20, 0)

    def create_portfolio_section_left(self):
        """
        Creates the left part of the portfolio section with assets list.
        """
        self.portfolio_section_left = QWidget()
        self.portfolio_section_left_layout = QVBoxLayout()
        self.portfolio_section_left.setStyleSheet("padding: 0px; margin: 0px;")
        self.portfolio_section_left.setLayout(self.portfolio_section_left_layout)
        self.portfolio_section_layout.addWidget(self.portfolio_section_left)
        self.top_bar = QWidget()
        self.top_bar.setStyleSheet("padding: 0px; margin: 0px;")
        self.top_bar_layout = QHBoxLayout()
        self.top_bar.setLayout(self.top_bar_layout)
        self.portfolio_section_left_layout.addWidget(self.top_bar)
        assets_label = QLabel("Assets")
        assets_label.setStyleSheet("color: #9B9B9B;")
        assets_label.setFont(QFont('Inter', 20, QFont.Weight.Light))
        self.top_bar_layout.addWidget(assets_label)
        self.top_bar_layout.addStretch(0)
        self.top_bar_layout.addWidget(self.currency_selector)
        self.currency_selector.setStyleSheet("""
            QComboBox {
                background-color: #777777;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Inter';
                font-size: 8pt;
                font-weight: semi-bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }                      
        """)
        self.currency_selector.activated.connect(self.on_currency_selected)
        self.add_portfolio_button = QPushButton("+  Add Holdings")
        self.add_portfolio_button.clicked.connect(self.open_form)
        self.add_portfolio_button.setStyleSheet("""
            QPushButton {
                background-color: #0062FF; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 5px;
                font-family: 'Inter';
                font-size: 8pt;
                font-weight: semi-bold;
                }
            QPushButton:hover {
                background-color: #0056b3;
                }                      """)
        self.add_portfolio_button.setFixedWidth(120)    
        self.add_portfolio_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_bar_layout.addWidget(self.currency_selector)
        self.top_bar_layout.addWidget(self.add_portfolio_button)     
        self.create_portfolio_assets_section()

    def create_portfolio_assets_section(self):
        """
        Creates the assets section with a scrollable list of holdings.
        """
        self.assets_scroll_area = IndependentScrollArea()
        self.assets_scroll_area.setStyleSheet("padding: 0px; margin: 0px; border: none;")
        self.assets_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.assets_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.assets_scroll_area.setWidgetResizable(True)
        self.assets_scroll_area.setFixedHeight(400)
        self.portfolio_section_left_layout.addWidget(self.assets_scroll_area)
        if self.portfolio_holdings:
            # Create a scrollable container widget
            self.assets_container = QWidget()
            self.assets_container.setStyleSheet("padding: 0px; margin: 0px;")
            self.assets_layout = QVBoxLayout(self.assets_container)
            self.assets_container.setLayout(self.assets_layout)
            # Assign the container widget to the scroll area
            self.assets_scroll_area.setWidget(self.assets_container)  
            self.assets_section = QWidget()
            self.assets_section_layout = QVBoxLayout()
            self.assets_layout.addWidget(self.assets_section)
            self.load_assets()
        else:
            no_assets_label = QLabel("No assets added yet.")
            no_assets_label.setFont(QFont('Inter', 15))
            self.assets_scroll_area.setWidget(no_assets_label)
            self.portfolio_section_left_layout.setContentsMargins(20, 20, 20, 20)
            self.portfolio_section_left_layout.addStretch(0)

    def open_form(self):
        """
        Opens a form dialog for adding new holdings.
        """
        self.input_fields = []
        self.form = QDialog()
        self.form.setWindowTitle("Add Holdings")
        self.form.setFixedSize(400, 600)
        self.form_layout = QVBoxLayout(self.form)
        self.form.setLayout(self.form_layout)
        add_investment_label = QLabel("Add Investment")
        add_investment_label.setFont(QFont('Inter', 15))
        self.form_layout.addWidget(add_investment_label)
        self.add_inputs()
        self.submit_button = QPushButton("Submit", self.form)
        self.form_layout.addWidget(self.submit_button)
        self.submit_button.clicked.connect(self.add_investment)
        self.form.exec()

    def save_portfolio(self):
        """
        Saves the current portfolio holdings to a CSV file.
        """
        if not self.portfolio_holdings:
            messagebox.showinfo("Save Portfolio", "No holdings to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        columns = ["Symbol", "Purchase Price", "Fees", "Units", "Date Purchased", "Category"]
        df = pd.DataFrame(self.portfolio_holdings, columns=columns)
        df.to_csv(file_path, index=False)
        messagebox.showinfo("Save Portfolio", f"Portfolio saved to {file_path}")

    def load_portfolio(self):
        """
        Loads portfolio holdings from a CSV file.
        """
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        try:
            df = pd.read_csv(file_path)
            required_columns = ["Symbol", "Purchase Price", "Fees", "Units", "Date Purchased", "Category"]
            if not all(col in df.columns for col in required_columns):
                messagebox.showerror("Load Portfolio", "Invalid file format.")
                return
            self.portfolio_holdings = df.values.tolist()
            self.update_portfolio([])
            messagebox.showinfo("Load Portfolio", f"Portfolio loaded from {file_path}")
        except Exception as e:
            messagebox.showerror("Load Portfolio", f"Error loading portfolio: {e}")

    def get_portfolio_data_for_graph(self, timeframe: str):
        """
        Returns a DataFrame with portfolio value over time for charting.
        """
        holdings = self.portfolio_holdings
        if not holdings:
            return pd.DataFrame(columns=["time", "price"])
        end_date = dt.datetime.now()
        # Map timeframe string to a start date
        delta_map = {
            "1wk": timedelta(weeks=1),
            "1mo": timedelta(days=30),
            "3mo": timedelta(days=90),
            "6mo": timedelta(days=180),
            "1y": timedelta(days=365),
            "2y": timedelta(days=730),
            "5y": timedelta(days=1825),
            "max": None
        }
        if timeframe not in delta_map:
            timeframe = "1mo"
        start_date = end_date - delta_map[timeframe] if delta_map[timeframe] else dt.datetime(2000, 1, 1)
        tasks = []
        for idx, h in enumerate(holdings):
            try:
                symbol = str(h[0]).strip()
                units = float(h[3])
                date_str = str(h[4]).strip()
                purchase_date = None
                for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        purchase_date = dt.datetime.strptime(date_str, fmt)
                        break
                    except Exception:
                        continue
                if not purchase_date:
                    purchase_date = pd.to_datetime(date_str, dayfirst=True)
                if purchase_date > end_date:
                    continue
                tasks.append((idx, symbol, units, purchase_date))
            except Exception as e:
                print("Skipping invalid holding:", h, "error:", e)
        if not tasks:
            return pd.DataFrame(columns=["time", "price"])

        def fetch(idx, symbol, units, start_dt):
            try:
                raw = yf.download(
                    symbol,
                    start=start_dt,
                    end=end_date + timedelta(days=1),
                    interval="1d",
                    progress=False,
                    auto_adjust=True
                )

                if raw is None or raw.empty:
                    print(f"No data returned for {symbol}")
                    return None

                if "Adj Close" in raw.columns:
                    series = raw["Adj Close"]
                elif "Close" in raw.columns:
                    series = raw["Close"]
                else:
                    return None

                series.index = pd.to_datetime(series.index)
                series = series * units
                series.name = f"{symbol}_{idx}"

                return series
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                return None

        dfs = []
        with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as executor:
            future_to_task = {executor.submit(fetch, idx, sym, units, max(start_date, dt)): (sym, idx)
                            for idx, sym, units, dt in tasks}
            for fut in as_completed(future_to_task):
                sym, idx = future_to_task[fut]
                try:
                    df = fut.result()
                    if df is not None and not df.empty:
                        dfs.append(df)
                except Exception as e:
                    print(f"Fetch thread failed for {sym}_{idx}: {e}")

        if not dfs:
            return pd.DataFrame(columns=["time", "price"])

        combined = pd.concat(dfs, axis=1, join="outer").fillna(0.0)
        combined["price"] = combined.sum(axis=1, numeric_only=True)
        out = combined[["price"]].reset_index()
        if "index" in out.columns:
            out.rename(columns={"index": "time"}, inplace=True)
        elif "Date" in out.columns:
            out.rename(columns={"Date": "time"}, inplace=True)

        # Format time as string for lightweight-charts
        out["time"] = pd.to_datetime(out["time"]).dt.strftime("%Y-%m-%d")
        out["price"] = out["price"].astype(float)

        print(f"Returning {len(out)} rows for timeframe {timeframe}: {out['time'].min()} → {out['time'].max()}")
        return out

    def get_form_values(self):
        """
        Retrieves values from the form input fields.
        """
        input_values = []   
        for input in self.input_fields:
            input_values.append(input.text())
        return input_values

    def check_properly_formatted(self, inputted_values):
        """
        Validates the format of inputted values.
        """
        error_string = ""
        for i, value in enumerate(inputted_values):
            if value == "":
                error_string += f"Field {self.input_list[i]['name']} is empty.\n"
            else:
                if self.input_list[i]["type"] == "number":
                    try:
                        float(value)
                    except ValueError:
                        error_string += f"Field {self.input_list[i]['name']} is not properly formatted.\n"
                elif self.input_list[i]["type"] == "date":
                    try:
                        dt.datetime.strptime(value, "%d-%m-%Y")
                    except ValueError:
                        try:
                            dt.datetime.strptime(value, "%d/%m/%Y")
                        except ValueError:
                            try:
                                dt.datetime.strptime(value, "%Y-%m-%d")
                            except ValueError:
                                error_string += f"Field {self.input_list[i]['name']} is not properly formatted.\n"
                elif self.input_list[i]["type"] == "text":
                    if not value.isalnum():
                        error_string += f"Field {self.input_list[i]['name']} is not properly formatted.\n"
        if error_string != "":
            messagebox.showerror("Input Error", f"Please correct the following errors:\n{error_string}")
            return False
        else:
            return True

    def add_investment(self):
        """
        Adds a new investment to the portfolio after validation.
        """
        text_values = self.get_form_values()
        if self.check_properly_formatted(text_values):   
            self.update_portfolio(text_values)
        self.form.accept()
        self.input_fields = []
        
    def get_current_price(self, symbol):
        """
        Fetches the current price of a stock symbol.
        """
        try:
            data = yf.Ticker(symbol)
            return data.history(period="1d")["Close"].iloc[-1]
        except Exception as e:
            messagebox.showerror("Portfolio Update", f"Error fetching data for {symbol}: {e}")
            return 0
    
    def group_portfolio_holdings(self):
        """
        Groups holdings by symbol for aggregation.
        """
        grouped = {}
        for holding in self.portfolio_holdings:
            symbol = holding[0]
            if symbol not in grouped:
                grouped[symbol] = [holding[1:]]
            else:
                grouped[symbol].append(holding[1:])
        return grouped

    def update_portfolio(self, text_values):
        """
        Updates the portfolio with new data and recalculates metrics.
        """

        if len(text_values) > 0:
            # Remove duplicate append; only add the new holding once
            if len(text_values) == 5:
                new_holding = text_values + ["General"]
            else:
                new_holding = list(text_values)
            self.portfolio_holdings.append(new_holding)

        self.total_portfolio_holdings = []

        grouped_holdings = self.group_portfolio_holdings()
        edited_grouped_holdings = {}

        self.total_profit_loss = 0
        self.total_portfolio_value = 0

        self.daily_change = 0
        self.daily_change_percent = 0

        for symbol in grouped_holdings:
            try:
                finnhub_api_key = os.getenv('FINNHUB_API_KEY')
                data = requests.get(f"https://finnhub.io/api/v1/search?q={symbol}&token={finnhub_api_key}")
                result = data.json()

                 # WILL change
                first_holding = grouped_holdings[symbol][0]
                category = first_holding[4] if len(first_holding) > 4 else "General"
                

                purchase_date = dt.datetime.now().strftime("%d/%m/%Y") # dt.datetime.strptime(grouped_holdings[symbol][0][3], "%d-%m-%Y").date()

                name = result['result'][0]['description'] if result['count'] > 0 else symbol
                current_price = self.get_current_price(symbol)

                total_units = 0
                total_symbol_value = 0
                total_symbol_profit_loss = 0

                total_current_value = 0
                total_investment_value = 0
                
                i=0
                for holding in grouped_holdings[symbol]:
                    purchase_price = float(holding[0])

                    fees = float(holding[1])
                    units = float(holding[2])
                
                    total_investment = (purchase_price * units) - fees
                    current_value = current_price * units
                    profit_loss = current_value - total_investment

                    total_symbol_profit_loss += profit_loss
                    total_current_value += current_value
                    total_symbol_value += current_value
                    total_investment_value += total_investment
                    total_units += units
                    if i==0:
                        purchase_date = holding[3]
                        i+=1

                self.total_profit_loss += total_symbol_profit_loss
                self.total_portfolio_value += total_symbol_value
                self.total_portfolio_change = (self.total_profit_loss / (self.total_portfolio_value - self.total_profit_loss) * 100) if (self.total_portfolio_value - self.total_profit_loss) != 0 else 0
                
                edited_grouped_holdings[symbol] = [
                    name,
                    symbol,
                    total_units,
                    f"{CurrencySymbols.get_symbol(self.currency)}{self.convert_currency(total_symbol_value):.2f}",
                    (total_symbol_profit_loss / total_investment_value * 100) if total_investment_value != 0 else 0,
                    category,
                    purchase_date
                ]

            except Exception as e:
                messagebox.showerror("Portfolio Update", f"Error fetching data for {symbol}: {e}")

        if self.total_portfolio_value - self.total_profit_loss != 0:
            self.total_profit_loss_percent = (self.total_profit_loss / (self.total_portfolio_value - self.total_profit_loss) * 100)

        for edited_holding in edited_grouped_holdings:
            self.total_portfolio_holdings.append([
                edited_grouped_holdings[edited_holding][0], #name
                edited_grouped_holdings[edited_holding][1], #symbol
                edited_grouped_holdings[edited_holding][2], #units
                edited_grouped_holdings[edited_holding][3], #total investment price
                edited_grouped_holdings[edited_holding][4], #Profit loss percentage
                edited_grouped_holdings[edited_holding][5], #category
                edited_grouped_holdings[edited_holding][6] #purchase date
            ])

        self.calculate_daily_change()
        self.update_portfolio_display()    

    def update_text_values(self):
        """
        Updates the text labels with current portfolio values.
        """
        self.portfolio_value_label.setText(f"{CurrencySymbols.get_symbol(self.currency)}{self.total_portfolio_value:,.2f}")
        self.portfolio_change_label_text.setText(f"{self.total_portfolio_change:.2f}%")
        self.profit_loss_label.setText(f"{CurrencySymbols.get_symbol(self.currency)}{self.total_profit_loss:.2f}")
        self.profit_loss_label_text.setText(f"{self.total_profit_loss_percent:.2f}%")
        self.daily_change_label.setText(f"{CurrencySymbols.get_symbol(self.currency)}{self.daily_change:.2f}")
        self.daily_change_label_text.setText(f"{self.daily_change_percent:.2f}%")

        self.portfolio_change_label_text.setStyleSheet(f"color: {self.determine_color(self.total_portfolio_change)};")
        self.profit_loss_label_text.setStyleSheet(f"color: {self.determine_color(self.total_profit_loss_percent)};")
        self.daily_change_label_text.setStyleSheet(f"color: {self.determine_color(self.daily_change_percent)};")

        self.portfolio_change_label.setPixmap(self.determine_icon(self.total_portfolio_change))
        self.profit_loss_icon.setPixmap(self.determine_icon(self.total_profit_loss_percent))
        self.daily_change_icon.setPixmap(self.determine_icon(self.daily_change_percent))

    def update_assets_list(self):
        """
        Updates the assets list display.
        """
        self.portfolio_section_left_layout.removeWidget(self.assets_scroll_area)
        self.assets_scroll_area.deleteLater()
        self.create_portfolio_assets_section()
        
    def update_graph(self, timeframe="max"):
        """
        Updates the portfolio graph with new data.
        """
        data = self.get_portfolio_data_for_graph(timeframe)
        self.chart.watermark("Investmate")
        self.line.set(data)

    def update_portfolio_display(self):
        """
        Refreshes the entire portfolio display.
        """
        self.update_text_values()
        self.update_assets_list()
        self.update_graph()

    def calculate_daily_change(self):
        """
        Calculates the daily change for the portfolio.
        """
        for holding in self.total_portfolio_holdings:
            symbol = holding[1]
            data = yf.Ticker(symbol)
            self.daily_change += data.history(period="1d")["Close"].iloc[-1] - data.history(period="1d")["Open"].iloc[-1]
            self.daily_change_percent += ((data.history(period="1d")["Close"].iloc[-1] - data.history(period="1d")["Open"].iloc[-1]) / data.history(period="1d")["Open"].iloc[-1]) * 100

    def add_inputs(self):
        """
        Adds input fields to the form based on the input list.
        """
        for field in self.input_list:
            list_item = QWidget()
            list_item_layout = QVBoxLayout()
            label = QLabel(field["name"])
            label.setFont(QFont('Inter', 10))
            list_item_layout.addWidget(label)
            if field["type"] == "text" or  field["type"] == "number" and field["name"] != "Symbol":
                input_field = QLineEdit()
                self.input_fields.append(input_field)
            elif field["name"] == "Symbol":
                input_field = QLineEdit()
                completer = QCompleter(self.stock_autocomplete_values)
                input_field.setCompleter(completer)
                self.input_fields.append(input_field)
            elif field["type"] == "date":
                input_field = QDateEdit()
                self.input_fields.append(input_field)
                input_field.setCalendarPopup(True)
                input_field.setDate(dt.datetime.now())
            list_item_layout.addWidget(input_field)
            list_item.setLayout(list_item_layout)
            list_item_layout.addStretch(0)
            self.form_layout.addWidget(list_item)
        self.form_layout.addStretch(0)

    def load_assets(self):
        """
        Loads and displays the assets in the UI.
        """
        for holding in self.total_portfolio_holdings:
            asset_widget = QWidget()
            asset_layout = QHBoxLayout()
            asset_widget.setLayout(asset_layout)
            asset_widget.setStyleSheet("background-color: #262626; border-radius: 7px; padding 4px;")
            asset_widget.setFixedHeight(90)
            self.assets_layout.addWidget(asset_widget)
            logo_token = os.getenv('LOGO_DEV_TOKEN')
            logo = requests.get(f"https://img.logo.dev/ticker/{holding[1]}?token={logo_token}&size=64&retina=true")
            logo_image = QPixmap()
            logo_image.loadFromData(logo.content)
            logo_image = logo_image.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            asset_name_logo = QLabel()
            asset_name_logo.setPixmap(logo_image)
            asset_layout.addWidget(asset_name_logo)
            asset_middle_section = QWidget()
            asset_middle_layout = QVBoxLayout()
            asset_middle_section.setLayout(asset_middle_layout)
            asset_layout.addWidget(asset_middle_section)
            asset_middle_top_section = QWidget()
            asset_middle_top_layout = QHBoxLayout()
            asset_middle_top_section.setLayout(asset_middle_top_layout)
            asset_middle_layout.addWidget(asset_middle_top_section)
            asset_name = QLabel(holding[0])
            asset_name.setStyleSheet("color: white;")
            asset_name.setFont(QFont('Inter', 13))
            asset_middle_top_layout.addWidget(asset_name)
            asset_middle_top_layout.addSpacing(5)
            ticker_label = QLabel(f"${holding[1]}")
            ticker_label.setStyleSheet("color: #9B9B9B;")
            ticker_label.setFont(QFont('Inter', 8, QFont.Weight.Light))
            asset_middle_top_layout.addWidget(ticker_label)
            asset_middle_top_layout.addStretch(0)
            asset_middle_bottom_section = QWidget()
            asset_middle_bottom_layout = QHBoxLayout()
            asset_middle_bottom_section.setLayout(asset_middle_bottom_layout)
            asset_middle_layout.addWidget(asset_middle_bottom_section)
            units_label = QLabel(f"{int(holding[2]).__floor__()} Units")
            units_label.setStyleSheet("color: white;")
            units_label.setFont(QFont('Geist Mono', 9, QFont.Weight.Light))
            asset_middle_bottom_layout.addWidget(units_label)
            asset_middle_bottom_layout.addStretch(0)
            self.create_line_spacer(asset_middle_bottom_layout, 20)
            asset_middle_bottom_layout.addStretch(0)
            category_label = QLabel(holding[5])
            category_label.setStyleSheet("color: white;")
            category_label.setFont(QFont('Inter', 9, QFont.Weight.Light))
            asset_middle_bottom_layout.addWidget(category_label)
            asset_middle_bottom_layout.addStretch(0)
            self.create_line_spacer(asset_middle_bottom_layout, 20)
            asset_middle_bottom_layout.addStretch(0)
            date_label = QLabel(holding[6])
            date_label.setStyleSheet("color: white;")
            date_label.setFont(QFont('Geist Mono', 9, QFont.Weight.Light))
            asset_middle_bottom_layout.addWidget(date_label)
            asset_middle_bottom_layout.addStretch(0)
            asset_right_section = QWidget()
            asset_right_layout = QVBoxLayout()
            asset_right_section.setLayout(asset_right_layout)
            asset_layout.addWidget(asset_right_section)
            asset_right_layout.setContentsMargins(0, 0, 0, 0)
            asset_prices_section = QWidget()
            asset_prices_section.setStyleSheet("padding: 0px; margin: 0px;")
            asset_prices_layout = QHBoxLayout() 
            asset_prices_section.setLayout(asset_prices_layout)
            asset_right_layout.addWidget(asset_prices_section)
            asset_right_layout.addStretch(0)
            price_label = QLabel(holding[3])
            price_label.setStyleSheet("color: white;") 
            price_label.setFont(QFont('Geist Mono', 12))
            asset_prices_layout.addWidget(price_label)
            asset_prices_layout.addSpacing(10)
            price_change_icon = QLabel()
            price_change_icon.setPixmap(self.determine_icon(holding[4]))
            asset_prices_layout.addWidget(price_change_icon)
            price_change_label = QLabel(f"{holding[4]:.2f}%")
            price_change_label.setStyleSheet(f"color: {self.determine_color(holding[4])};")
            price_change_label.setFont(QFont('Inter', 10, QFont.Weight.Light))
            asset_prices_layout.addWidget(price_change_label)
            asset_layout.setContentsMargins(20, 20, 20, 20)
            asset_prices_layout.setContentsMargins(0, 0, 0, 0)
            asset_middle_layout.setContentsMargins(0, 0, 0, 0)
            asset_middle_top_layout.setContentsMargins(5, 0, 0, 0)
            asset_middle_bottom_layout.setContentsMargins(5, 0, 0, 0)
            self.assets_container.setContentsMargins(0, 0, 0, 0)
            self.portfolio_section_left_layout.setContentsMargins(0, 0, 0, 0)

            self.assets_layout.addSpacing(10)

        self.assets_layout.addStretch(0)
        self.portfolio_section_left_layout.addStretch(0)
           
    def create_portfolio_section_right(self):
        """
        Creates the right part of the portfolio section with chart and save/load buttons.
        """
        self.portfolio_section_right = QWidget()
        self.portfolio_section_right_layout = QVBoxLayout()
        self.portfolio_section_right_layout.setContentsMargins(20, 0, 0, 0)
        self.portfolio_section_right.setLayout(self.portfolio_section_right_layout)
        self.portfolio_section_layout.addWidget(self.portfolio_section_right)
        self.portfolio_section_right_top_bar = QWidget()
        self.portfolio_section_right_top_bar.setStyleSheet("padding: 0px; margin: 0px;")
        self.portfolio_section_right_top_bar_layout = QHBoxLayout()
        self.portfolio_section_right_top_bar.setLayout(self.portfolio_section_right_top_bar_layout)
        self.portfolio_section_right_layout.addWidget(self.portfolio_section_right_top_bar)
        self.portfolio_section_right_top_bar_layout.setContentsMargins(0, 0, 0, 0)
        portfolio_label = QLabel("Portfolio")
        portfolio_label.setFont(QFont('Inter', 20, QFont.Weight.Light))
        portfolio_label.setStyleSheet("color: #9B9B9B;")
        self.portfolio_section_right_top_bar_layout.addWidget(portfolio_label)
        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #0062FF; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 5px;
                font-family: 'Inter';
                font-size: 8pt;
                font-weight: semi-bold;
                }
                QPushButton:hover {
                background-color: #0056b3;
                }                      
                                       """
        )
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_portfolio)
        self.save_button.setFixedWidth(80)
        self.portfolio_section_right_top_bar_layout.addWidget(self.save_button)
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_portfolio)
        self.load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #0062FF; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 5px;
                font-family: 'Inter';
                font-size: 8pt;
                font-weight: semi-bold;
            }
                                       
            QPushButton:hover {
                background-color: #0056b3;
            }

        """
        )
        self.load_button.setFixedWidth(80)
        self.portfolio_section_right_top_bar_layout.addWidget(self.load_button)
        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout()
        self.chart_widget.setLayout(self.chart_layout)
        self.portfolio_section_right_layout.addWidget(self.chart_widget)
        self.chart = QtChart(self.chart_widget)
        self.line = self.chart.create_line("price")
        self.chart.legend(True)
        self.chart.topbar.switcher(
            'timeframe',
            ('1d', '1wk', '1mo', '6mo', '1y', "max"),
            default='max',
            func=self.on_timeframe_selection
        )
        self.chart_layout.addWidget(self.chart.get_webview())
        self.portfolio_section_right_layout.setStretch(0, 1)
        self.portfolio_section_right_layout.setStretch(1, 9)    

    def on_currency_selected(self):
        """
        Handles currency selection change.
        """
        self.currency = self.currency_selector.currentText()
        self.update_currency()
        self.update_portfolio([])

    def load_trending_news_data(self):
        """
        Fetches trending news data from an API.
        """
        try:
            news_api_key = os.getenv('NEWS_API_KEY')
            data = requests.get(f"https://newsapi.org/v2/everything?q=stock&sortBy=popularity&apiKey={news_api_key}")
            response = data.json()
            return response['articles'][:3]
        except requests.RequestException as e:
            messagebox.showerror("News Error", f"Error fetching news: {e}")

    def create_trending_news_section(self):
        """
        Creates the trending news section.
        """
        news_data = self.load_trending_news_data()
        trending_news_section = QWidget()
        trending_news_layout = QVBoxLayout()    
        trending_news_section.setLayout(trending_news_layout)
        self.main_scroll_area_layout.addWidget(trending_news_section)
        trending_news_label = QLabel("Trending News")
        trending_news_label.setFont(QFont('Inter', 20, QFont.Weight.Light))
        trending_news_layout.addWidget(trending_news_label)
        trending_news_list_section = QWidget()
        trending_news_list_layout = QHBoxLayout()    
        trending_news_list_section.setLayout(trending_news_list_layout)
        trending_news_layout.addWidget(trending_news_list_section)
        for article in news_data:
            news_widget = QWidget()
            news_widget.setStyleSheet("background-color: #262626; border-radius: 7px;")
            news_layout = QHBoxLayout()
            news_widget.setLayout(news_layout)
            trending_news_list_layout.addWidget(news_widget)
            image_data = urlopen(article["urlToImage"])
            news_image = QLabel()
            news_image.setStyleSheet("""
                                     QLabel {
                                     border-radius: 5px;
                                     }""")
            news_image_pixmap = QPixmap()
            news_image_pixmap.loadFromData(image_data.read())
            news_image.setPixmap(news_image_pixmap.scaled(150, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            news_layout.addWidget(news_image)
            news_layout.addStretch(0)
            news_widget_right = QWidget()
            news_widget_right.setStyleSheet("padding: 0px; margin: 0px;")
            news_widget_right_layout = QVBoxLayout()
            news_widget_right.setLayout(news_widget_right_layout)
            news_layout.addWidget(news_widget_right)
            title_section = QWidget()
            title_section_layout = QHBoxLayout()
            title_section.setLayout(title_section_layout)
            news_widget_right_layout.addWidget(title_section)
            news_title = QLabel(article['title'])
            news_title.setWordWrap(True)
            news_title.setFont(QFont('Inter', 10, QFont.Weight.Bold))
            news_title.setStyleSheet("color: white;")
            title_section_layout.addWidget(news_title)
            date_label = QLabel(article['publishedAt'].split('T')[0])
            date_label.setFont(QFont('Inter', 7, QFont.Weight.Light))
            date_label.setStyleSheet("color: #9B9B9B;")
            title_section_layout.addWidget(date_label)
            title_section_layout.addStretch(0)
            description_label = QLabel(article['description'])
            description_label.setFont(QFont('Inter', 5, QFont.Weight.Light))
            description_label.setWordWrap(True)
            description_label.setStyleSheet("color: white;")
            news_widget_right_layout.addWidget(description_label)
            news_widget_right_layout.addStretch(0)
            read_more_label = QLabel(f"<a href='{article['url']}'>Read More</a>")
            read_more_label.setOpenExternalLinks(True)
            read_more_label.setFont(QFont('Inter', 10, QFont.Weight.Light))
            read_more_label.setStyleSheet("color: #0062FF;")
            news_widget_right_layout.addWidget(read_more_label)
            news_layout.setContentsMargins(0, 0, 0, 0)
            news_widget_right_layout.setContentsMargins(0, 20, 10, 20)
            title_section_layout.setContentsMargins(0, 0, 0, 0)
            news_layout.setStretch(0, 0)
            news_layout.setStretch(1, 3)

    def set_selected_stock(self, stock):
        """
        Sets the selected stock for the stock screen.
        """
        self.stock_screen.set_selected_stock(stock)

    def initalise_ui(self):
        """
        Initializes the entire UI.
        """
        self.initalise_fonts()
        self.create_header()
        self.create_screens()
        self.create_info_section()
        self.create_portfolio_section()
        self.create_trending_news_section()

    def run_clock(self):
        """
        Updates the clock display.
        """
        now = dt.datetime.now().strftime('%H:%M:%S %p')
        self.time_label.setText(now)
        
    def run(self):
        """
        Starts the application UI and clock.
        """
        self.initalise_ui()
        self.run_clock()
        self.show()

    def on_timeframe_selection(self, chart):
        """
        Handles timeframe selection for the chart.
        """
        self.update_graph(chart.topbar['timeframe'].value)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = invest_mate()
    window.run()
    app.exec()