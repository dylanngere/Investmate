# search_screen.py
from tkinter import messagebox
from urllib.request import urlopen
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QCompleter, QScrollArea, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
import requests
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import yfinance as yf
from PyQt6.QtGui import QFont, QPixmap, QDesktopServices
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Custom canvas for displaying sparklines (mini charts).
class SparklineCanvas(FigureCanvas):
    """
    A custom FigureCanvas for rendering small sparkline charts.
    """
    def __init__(self, prices):
        fig = Figure(figsize=(2, 0.5))
        fig.patch.set_alpha(0)  # Transparent background.
        super().__init__(fig)
        ax = fig.add_subplot(111)
        ax.plot(prices, linewidth=1.2, color=("#14AE5C" if prices[-1] > prices[0] else "#F24822"))  # Green if up, red if down.
        ax.set_facecolor("none") 
        ax.axis("off")
        
        ax.margins(x=0)

# Worker thread for fetching stock search results asynchronously.
class StockSearchWorker(QThread):
    """Worker thread for fetching stock search results"""
    results_ready = pyqtSignal(list)
    
    def __init__(self, query):
        super().__init__()
        self.query = query

    def set_loading_cursor(self, loading: bool):
        """
        Sets the application-wide cursor to indicate loading.
        """
        if loading:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
    
    def run(self):
        """
        Executes the search query in a separate thread.
        """
        self.set_loading_cursor(True)
        try:
            finnhub_api_key = os.getenv('FINNHUB_API_KEY')
            data = requests.get(
                f"https://finnhub.io/api/v1/search?q={self.query}&token={finnhub_api_key}",
                timeout=5
            )
            if data.status_code == 200:
                results = data.json().get("result", [])
                symbols = [item["symbol"] for item in results]
                self.results_ready.emit(symbols)
            else:
                self.results_ready.emit([])
                
        except Exception as e:
            print(f"Error fetching stock data: {e}")
            self.results_ready.emit([])

        self.set_loading_cursor(False)

# Main search screen widget for stock search and news display.
class SearchScreen(QtWidgets.QWidget):
    """
    The search screen widget, handling stock search, autocomplete, indices display, and news.
    """
    def __init__(self, switch_tabs_callback, set_selected_stock_callback):
        super().__init__()
        self.stock_autocomplete_values = []
        self.switch_tabs = switch_tabs_callback
        self.set_selected_stock = set_selected_stock_callback
        self.search_worker = None
        self.run()
    
    def determine_color(self, value):
        """
        Determines the color based on the value's sign.
        """
        if value > 0:
            return "#14AE5C"  # Green for positive
        elif value < 0:
            return "#F24822"  # Red for negative
        else:
            return "#9B9B9B"  # Grey for neutral
        
    def determine_icon(self, value, size=9):
        """
        Determines the icon based on the value's sign.
        """
        if value > 0:
            return QPixmap('images/up-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif value < 0:
            return QPixmap('images/down-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)  
        else:    
            return QPixmap('')  
        
    def create_search_section(self):
        """
        Creates the search section with input and indices.
        """
        self.search_section = QWidget()
        self.search_section.setFixedHeight(200)
        self.search_section_layout = QHBoxLayout()
        self.search_section.setLayout(self.search_section_layout)
        self.search_screen_layout.addWidget(self.search_section)

        self.create_search_section_left()
        self.create_search_section_right()

    def handle_stock_autocomplete_values(self):
        """
        Handles text changes in the search input to trigger autocomplete.
        """
        text = self.search_label_input.text()
        if len(text) < 2:
            self.completer.model().setStringList([])
            return
        
        # Start new search
        self.search_worker = StockSearchWorker(text)
        self.search_worker.results_ready.connect(self.update_autocomplete)
        self.search_worker.start()

    
    def update_autocomplete(self, symbols):
        """
        Updates the completer with fetched symbols.
        """
        self.stock_autocomplete_values = symbols
        if symbols == []:
            return
        model = self.completer.model()
        for symbol in symbols:
            if model.insertRow(model.rowCount()):
                index = model.index(model.rowCount() - 1, 0)
                model.setData(index, symbol)

    def create_search_section_left(self):
        """
        Creates the left part of the search section with input field.
        """
        self.search_section_left = QWidget()
        self.search_section_left_layout = QVBoxLayout()
        self.search_section_left.setLayout(self.search_section_left_layout)
        self.search_section_layout.addWidget(self.search_section_left)

        search_label = QLabel("Search")
        search_label.setFont(QFont('Inter', 30, QFont.Weight.Light))
        search_label.setStyleSheet("color: white;")
        self.search_section_left_layout.addWidget(search_label)

        self.search_section_left_layout.addStretch(0)

        self.search_label_input = QLineEdit()
        self.search_label_input.returnPressed.connect(self.search_news)
        self.search_label_input.textChanged.connect(self.handle_stock_autocomplete_values)
        self.completer = QCompleter(self.stock_autocomplete_values)
        self.completer.activated.connect(self.on_completer_activated)
        self.search_label_input.setCompleter(self.completer)
        self.search_label_input.setPlaceholderText("Search here")
        self.search_label_input.setStyleSheet("""
            QLineEdit {
                background-color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 10px; 
                padding-left: 10px; /* to make space for the icon */
                color: #777777;
                font-family: 'Inter';
                font-size: 10pt;
            }""")

        self.search_section_left_layout.addWidget(self.search_label_input)

    def on_completer_activated(self, stock):
        """
        Handles selection from autocomplete to set selected stock.
        """
        self.search_label_input.text()
        self.set_selected_stock(stock)
        
    def calculate_change(self, data):
        """
        Calculates the percentage change from the first to last value in data.
        """
        values = data['Close'].values

        if len(values) < 2:
            return 0.0
        return float(((values[-1] - values[0]) / values[0]) * 100)

    def create_search_section_right(self):
        """
        Creates the right part with stock indices and sparklines.
        """
        self.search_section_right = QWidget()
        self.search_section_right_layout = QVBoxLayout()
        self.search_section_right_layout.setContentsMargins(0, 20, 0, 0)
        self.search_section_right.setLayout(self.search_section_right_layout)
        self.search_section_layout.addWidget(self.search_section_right)

        stock_indicies_label = QLabel("Stock Indicies")
        stock_indicies_label.setFont(QFont('Inter', 15, QFont.Weight.Light))
        stock_indicies_label.setStyleSheet("color: #9B9B9B;")
        self.search_section_right_layout.addWidget(stock_indicies_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.search_section_right_layout.addStretch(0)

        self.indicies_section = QWidget()
        self.indicies_section_layout = QHBoxLayout()
        self.indicies_section_layout.setContentsMargins(0, 0, 0, 0)
        self.indicies_section.setLayout(self.indicies_section_layout)
        self.search_section_right_layout.addWidget(self.indicies_section)

        symbols = [{"ticker": "^GSPC", "name": "S&P 500"}, {"ticker": "^AXJO", "name": "ASX 200"}, {"ticker": "^IXIC", "name": "NASDAQ"}]

        for s in symbols:
            price_data = yf.Ticker(s["ticker"])
            price = price_data.history(period="1d")["Close"].iloc[-1]

            indicie_widget = QWidget()
            indicie_layout = QHBoxLayout()
            indicie_layout.setContentsMargins(0, 0, 0, 0)
            indicie_widget.setLayout(indicie_layout)
            indicie_widget.setFixedSize(260, 100)
            self.indicies_section_layout.addWidget(indicie_widget)

            indicie_section_left = QWidget()
            indicie_section_left_layout = QVBoxLayout()
            indicie_section_left.setLayout(indicie_section_left_layout)
            indicie_layout.addWidget(indicie_section_left)

            text_section = QWidget()
            text_section_layout = QHBoxLayout()
            text_section.setLayout(text_section_layout)
            indicie_section_left_layout.addWidget(text_section)

            indicie_label = QLabel(s["name"])
            indicie_label.setFont(QFont('Inter', 13, QFont.Weight.Light))
            text_section_layout.addWidget(indicie_label)


            indicie_ticker = QLabel(f"({s['ticker']})")
            indicie_ticker.setStyleSheet("color: #777777;")
            indicie_ticker.setFont(QFont('Inter', 8, QFont.Weight.Light))
            text_section_layout.addWidget(indicie_ticker)
            
            text_section_layout.addStretch(0)

            prices_section = QWidget()
            prices_section_layout = QHBoxLayout()
            prices_section.setLayout(prices_section_layout)
            indicie_section_left_layout.addWidget(prices_section)

            indicie_price = QLabel(f"${price:.2f}")
            indicie_price.setFont(QFont('Geist Mono', 13, QFont.Weight.Light))
            prices_section_layout.addWidget(indicie_price)

            prices_section_layout.addStretch(0)

            data = yf.download(s["ticker"], period="1mo", interval="1d")
            change = self.calculate_change(data)

            change_widget = QWidget()
            change_layout = QHBoxLayout()
            change_layout.setContentsMargins(0, 0, 0, 0)
            change_widget.setLayout(change_layout)
            prices_section_layout.addWidget(change_widget)

            indicie_image = QLabel()
            indicie_image.setPixmap(self.determine_icon(change, size=6))
            change_layout.addWidget(indicie_image)

            indicie_change = QLabel(f"{change:.2f}%") 
            indicie_change.setFont(QFont('Geist Mono', 10, QFont.Weight.Light))
            indicie_change.setStyleSheet(f"color: {self.determine_color(change)}")
            change_layout.addWidget(indicie_change)
            
            sparkline = SparklineCanvas(data["Close"].values)
            sparkline.setStyleSheet("background: transparent;")
            sparkline.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            indicie_layout.addWidget(sparkline)
            

        self.search_section_right_layout.addStretch(0)

    def load_news(self, query):
        """
        Loads news articles based on the query.
        """
        try:
            news_api_key = os.getenv('NEWS_API_KEY')
            data = requests.get(f"https://newsapi.org/v2/everything?q={query}-stock&sortBy=popularity&apiKey={news_api_key}")
            response = data.json()

            return response['articles'][:20]
        
        except requests.RequestException as e:
            messagebox.showerror("News Error", f"Error fetching news: {e}")

    def search_news(self):
        """
        Searches for news based on the input query.
        """
        try:
            news_api_key = os.getenv('NEWS_API_KEY')
            data = requests.get(f"https://newsapi.org/v2/everything?q={self.search_label_input.text()}-stock&sortBy=popularity&apiKey={news_api_key}")
            response = data.json()
            
            self.news_section_layout.removeWidget(self.news_items_container)
            self.news_items_container.deleteLater()
            self.create_news_section(response['articles'][:20])
        
        except requests.RequestException as e:
            messagebox.showerror("News Error", f"Error fetching news: {e}")

    def display_news_container(self):
        """
        Sets up the scrollable news container.
        """
        self.search_scroll_area = QScrollArea()
        self.search_scroll_area.setStyleSheet("border: none;")
        self.search_scroll_area.setWidgetResizable(True)

        self.search_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.search_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.search_screen_layout.addWidget(self.search_scroll_area)

        self.news_section = QWidget()
        self.news_section_layout = QVBoxLayout()
        self.news_section.setLayout(self.news_section_layout)
        self.search_scroll_area.setWidget(self.news_section)


    def create_news_section(self, data):
        """
        Creates the news section with article widgets.
        """
        self.news_items_container = QWidget()
        self.news_items_container_layout = QVBoxLayout()
        self.news_items_container.setLayout(self.news_items_container_layout)
        self.news_section_layout.addWidget(self.news_items_container)

        for article in data:
            news_item = QWidget()
            news_item.setFixedSize(1450, 250)
            news_item.setContentsMargins(20, 20, 20, 20)
            news_layout = QHBoxLayout()
            news_item.setLayout(news_layout)
            news_item.setStyleSheet("background-color: #2E2E2E; border-radius: 7px;")
            self.news_items_container_layout.addWidget(news_item)
            try:
                image_data = urlopen(article["urlToImage"])
            except Exception as e:
                print(f"Error loading image: {e}")
                continue

            news_image = QLabel()
            news_image.setStyleSheet("""
                                     QLabel {
                                     border-radius: 5px;
                                     }""")
            
            news_image_pixmap = QPixmap()
            news_image_pixmap.loadFromData(image_data.read())
            news_image.setPixmap(news_image_pixmap.scaled(250, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            news_layout.addWidget(news_image)


            news_info_section = QWidget()
            news_info_layout = QVBoxLayout()
            news_info_section.setLayout(news_info_layout)
            news_layout.addWidget(news_info_section)

            news_title = QLabel(article['title'])
            news_title.setFont(QFont('Inter', 20, QFont.Weight.Bold))
            news_info_layout.addWidget(news_title)

            news_date = QLabel(article['publishedAt'].split('T')[0])
            news_date.setStyleSheet("color: #777777;")
            news_date.setFont(QFont('Inter', 10, QFont.Weight.Light))
            news_info_layout.addWidget(news_date)

            news_info_layout.addStretch(0)

            news_text = QLabel(article['description'])
            news_text.setWordWrap(True)
            news_text.setStyleSheet("color: white;")
            news_info_layout.addWidget(news_text)

            news_button = QtWidgets.QPushButton("Read More")
            news_button.setFixedWidth(300)
            news_button.clicked.connect(lambda _, url=article['url']: QDesktopServices.openUrl(QUrl(url)))
            news_button.setStyleSheet("""
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-family: 'Inter';
                    font-size: 12pt;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056A0;
                }
            """)
            news_info_layout.addWidget(news_button)
            news_layout.setStretch(1, 2)
        
        

    def run(self):
        """
        Initializes the search screen UI.
        """
        self.search_screen_layout = QVBoxLayout()
        self.setLayout(self.search_screen_layout)
        self.create_search_section()
        data = self.load_news("stock")
        self.display_news_container()
        self.create_news_section(data)