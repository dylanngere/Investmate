# stock_screen.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QFrame, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QUrl   
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from lightweight_charts.widgets import QtChart
import pandas as pd
import requests
import yfinance as yf
import os
from tkinter import messagebox
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# with open('chart.html', 'r', encoding='utf-8') as f:
#     chart_html = f.read()

class BarChartWidget(QWidget):
    """
    A widget that displays a bar chart of analyst recommendations for a given stock.
    """
    def __init__(self, stock):
        super().__init__()
        self.setFixedSize(300, 200)
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        self.stock = stock
        self.analyst_consensus = ""
        self.analyst_consensus_color = ""
        self.category = ""
        self.description = ""

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

        self.plot()

    def plot(self):
        """
        Fetches analyst recommendation data and plots the bar chart.
        """
        try:
            finnhub_api_key = os.getenv('FINNHUB_API_KEY')
            response = requests.get(f"https://finnhub.io/api/v1/stock/recommendation?symbol={self.stock}&token={finnhub_api_key}")
            data = response.json()[0]
            values = [data['strongSell'], data['sell'], data['hold'], data['buy'], data['strongBuy']]

            # Determine consensus based on the highest value.
            if values[0] == max(values):
                self.analyst_consensus = "Strong Sell"
                self.analyst_consensus_color = "#F24822"
            elif values[1] == max(values):
                self.analyst_consensus = "Sell"
                self.analyst_consensus_color = "#FF6600"
            elif values[2] == max(values):
                self.analyst_consensus = "Hold"
                self.analyst_consensus_color = "#FFF200"
            elif values[3] == max(values):
                self.analyst_consensus = "Buy"
                self.analyst_consensus_color = "#14AE5C"
            else:
                self.analyst_consensus = "Strong Buy"
                self.analyst_consensus_color = "#144F30"

            categories = ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]
            values = [data['strongSell'], data['sell'], data['hold'], data['buy'], data['strongBuy']]
            colors = ["#F24822", "#FF6600", "#FFF200", "#14AE5C", "#144F30"]  # each bar has its own color

            ax = self.figure.add_subplot(111)
            bars = ax.bar(categories, values, color=colors)

            # Add value labels above each bar
            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(value) if value != 0 else "",
                    ha='center', va='bottom',
                    color='white', fontsize=10
                )

            # Transparent background and minimal design
            self.figure.patch.set_alpha(0)
            ax.set_facecolor("none")
            for spine in ax.spines.values():
                spine.set_visible(False)

            ax.tick_params(axis='x', colors='white', labelsize=7)
            ax.yaxis.set_visible(False)
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Error fetching analyst recommendations: {e}")

    def resizeEvent(self, event):
        """
        Handles widget resizing to adjust the figure size.
        """
        self.figure.set_size_inches(self.width() / 100, self.height() / 100)
        self.figure.tight_layout(pad=0)
        self.canvas.draw()
        super().resizeEvent(event)

# Main widget for displaying detailed stock information.
class StockScreen(QWidget):
    """
    The main screen widget for displaying stock details, including charts, metrics, and financials.
    """
    def __init__(self):
        super().__init__()
        self.stock = ""

    def set_selected_stock(self, stock):
        """
        Sets the selected stock and fetches initial data.
        """
        self.stock = stock

        fmp_api_key = os.getenv('FINANCIAL_MODELING_PREP_API_KEY')
        data = requests.get(f"https://financialmodelingprep.com/stable/profile?symbol={self.stock[0]}&apikey={fmp_api_key}").json()
        self.description = data[0]['description']
        self.category = data[0]['industry']
        self.update_display()
        
    def update_display(self):
        """
        Updates the display with new stock data.
        """
        self.run()

    def init_ui(self):
        """
        Initializes the UI layout for the stock screen.
        """
        self.stock_layout = QVBoxLayout()
        self.setLayout(self.stock_layout)

        self.stock_scroll_area = QScrollArea()
        self.stock_scroll_area.setStyleSheet("border: none;")
        self.stock_scroll_area.setWidgetResizable(True)

        self.stock_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stock_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.stock_layout.addWidget(self.stock_scroll_area)

        self.stock_container = QWidget()
        self.stock_scroll_area.setWidget(self.stock_container)
        self.stock_container_layout = QVBoxLayout()
        self.stock_container.setLayout(self.stock_container_layout)
        self.stock_scroll_area.setWidget(self.stock_container)

    def get_current_price(self, symbol):
        """
        Gets the current price for a given stock symbol using yfinance.
        """
        try:
            data = yf.Ticker(symbol)
            return data.history(period="1d")["Close"].iloc[-1]
        except Exception as e:
            messagebox.showerror("Portfolio Update", f"Error fetching data for {symbol}: {e}")
            return 0

    def create_stock_info_section_left(self):
        """
        Creates the left section of the stock info, including top and bottom parts.
        """
        self.stock_info_section_left = QWidget()
        self.stock_info_layout_left = QVBoxLayout()
        self.stock_info_layout_left.setContentsMargins(0, 0, 0, 0)
        self.stock_info_section_left.setLayout(self.stock_info_layout_left)
        self.stock_info_layout.addWidget(self.stock_info_section_left)

        self.create_top_section()
        self.stock_info_layout_left.addSpacing(20)
        self.create_bottom_section()

    def calculate_daily_change(self):
        """
        Calculates the daily change and percent change for the stock.
        """

        symbol = self.ticker
        data = yf.Ticker(symbol)

        return ((data.history(period="1d")["Close"].iloc[-1] - data.history(period="1d")["Open"].iloc[-1]) / data.history(period="1d")["Open"].iloc[-1]) * 100

    def determine_color(self, value):
        """
        Determines the color based on the value's sign.
        """
        if value > 0:
            return "#14AE5C"  # Green for positive values
        elif value < 0:
            return "#F24822"  # Red for negative values
        else:
            return "#9B9B9B"  # Grey for neutral values
        
    def determine_icon(self, value, size=9):
        """
        Determines the icon based on the value's sign.
        """
        if value > 0:
            return QPixmap('images/up-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif value < 0:
            return QPixmap('images/down-circle.png').scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)  
        else:    
            return QPixmap('')  # Grey for neutral values

    def get_stock_data(self):
        """
        Retrieves and sets stock data attributes.
        """
        # Placeholder for actual stock data retrieval logic
        self.ticker = self.stock[0]
        finnhub_api_key = os.getenv('FINNHUB_API_KEY')
        name = requests.get(f"https://finnhub.io/api/v1/search?q={self.ticker}&token={finnhub_api_key}",).json()['result'][0]['description']
        self.stock_name = name.replace("Inc A", "")
        self.price = self.get_current_price(self.ticker)
        self.units = self.stock[1]
        self.daily_change_percent = self.calculate_daily_change()

    def create_top_section(self):
        """
        Creates the top section with stock logo, name, price, and changes.
        """

        self.get_stock_data()
        self.top_section = QWidget()
        self.top_section.setFixedHeight(150)
        self.top_section.setContentsMargins(0, 0, 0, 0)
        self.top_layout = QHBoxLayout()
        self.top_section.setLayout(self.top_layout)
        self.stock_info_layout_left.addWidget(self.top_section)

        logo_token = os.getenv('LOGO_DEV_TOKEN')
        logo = requests.get(f"https://img.logo.dev/ticker/{self.ticker}?token={logo_token}&size=64&retina=true")
        logo_image = QPixmap()
        logo_image.loadFromData(logo.content)
        logo_image = logo_image.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self.stock_image  = QLabel()
        self.stock_image.setPixmap(logo_image)
        self.top_layout.addWidget(self.stock_image)

        self.text_container = QWidget()
        self.text_layout = QVBoxLayout()
        self.text_container.setLayout(self.text_layout)
        self.top_layout.addWidget(self.text_container)

        self.text_layout.setContentsMargins(10, 0, 0, 10)
        self.prices_name_section = QWidget()
        self.prices_name_layout = QHBoxLayout()
        self.prices_name_layout.setContentsMargins(0, 0, 0, 0)
        self.prices_name_section.setLayout(self.prices_name_layout)
        self.text_layout.addWidget(self.prices_name_section)

        self.company_name_label = QLabel(self.stock_name)
        self.company_name_label.setFont(QFont('Inter', 25, QFont.Weight.Bold))
        self.company_name_label.setStyleSheet("color: white;")
        self.prices_name_layout.addWidget(self.company_name_label)

        self.prices_name_layout.addStretch(0)

        self.price_label = QLabel(f"${self.price:.2f}")
        self.price_label.setFont(QFont('Geist Mono', 25, QFont.Weight.Light))
        self.prices_name_layout.addWidget(self.price_label)

        self.changes_section = QWidget()
        self.changes_layout = QHBoxLayout()
        self.changes_layout.setContentsMargins(0, 0, 0, 0)
        self.changes_section.setLayout(self.changes_layout)
        self.text_layout.addWidget(self.changes_section)

        self.changes_layout.addStretch(0)

        self.change_image = QLabel()    
        self.change_image.setPixmap(self.determine_icon(self.daily_change_percent, size=15))
        self.changes_layout.addWidget(self.change_image)

        self.change_label = QLabel(f"{self.daily_change_percent:.2f}%")
        self.change_label.setStyleSheet(f"color: {self.determine_color(self.daily_change_percent)};")
        self.change_label.setFont(QFont('Inter', 15, QFont.Weight.Light))
        self.changes_layout.addWidget(self.change_label)

        if self.units > 0:
            self.unit_label = QLabel(f"{self.units} units")
            self.unit_label.setFont(QFont('Geist Mono', 13))
            self.text_layout.addWidget(self.unit_label)


        self.category_label = QLabel(self.category)
        self.category_label.setFont(QFont('Inter', 13, QFont.Weight.Light))
        self.text_layout.addWidget(self.category_label)


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
        
    def create_horizontal_line(self, layout, width=None):
        """
        Creates a horizontal line and adds it to the given layout.
        """
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #777777; background-color: #777777; border-radius: 5px;")
        if width:
            line.setFixedWidth(width)

        layout.addWidget(line)

    def check_value(self, value):
        """
        Checks and formats a value, returning 'N/A' if invalid.
        """
        if value is None or value == "":
            return "N/A"
        return f"{value:.2f}"

    def create_bottom_section(self):
        """
        Creates the bottom section with metrics and analyst consensus.
        """
        metrics_label = QLabel("Metrics")
        metrics_label.setFont(QFont('Inter', 25))
        self.stock_info_layout_left.addWidget(metrics_label)

        self.bottom_section = QWidget()
        self.bottom_section.setFixedHeight(300)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_section.setLayout(self.bottom_layout)

        self.bottom_left_section = QWidget()
        self.bottom_left_layout = QVBoxLayout()
        self.bottom_left_section.setLayout(self.bottom_left_layout)
        self.bottom_layout.addWidget(self.bottom_left_section)
        
        finnhub_api_key = os.getenv('FINNHUB_API_KEY')
        data = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={self.ticker}&metric=all&token={finnhub_api_key}").json()

        if len(data['metric']) == 0:
            no_data_label = QLabel("No metric data available.")
            no_data_label.setFont(QFont('Inter', 10))
            self.bottom_left_layout.addWidget(no_data_label)
            self.bottom_left_layout.addStretch(0)
            self.stock_info_layout_left.addWidget(self.bottom_section)
            return
        
        metric_data = []
        metric_labels = ["52 Week Range", "Volume", "P/E Annual", "Beta", "Revenue growth (5 yr)"]

        try:
            metric_data.append(f"${self.check_value(data.get('metric', {}).get('52WeekLow'))} - ${self.check_value(data.get('metric', {}).get('52WeekHigh'))}")
            metric_data.append(f"{self.check_value(data.get('metric', {}).get('10DayAverageTradingVolume'))}")
            metric_data.append(f"${self.check_value(data.get('metric', {}).get('peAnnual'))}")
            metric_data.append(f"{self.check_value(data.get('metric', {}).get('beta'))}")
            metric_data.append(f"{self.check_value(data.get('metric', {}).get('revenueGrowth5Y'))}")
        except Exception as error:
            print("Error fetching metric data:", error)

        for i in range(len(metric_labels)):
            metric_widget = QWidget()
            metric_layout = QVBoxLayout()
            metric_widget.setLayout(metric_layout)
            metric_widget.setFixedSize(300, 40)


            texts_widget = QWidget()
            texts_layout = QHBoxLayout()
            texts_widget.setLayout(texts_layout)
            metric_layout.addWidget(texts_widget)

            metric = QLabel(f"{metric_labels[i]}")
            metric.setFont(QFont('Inter', 8, QFont.Weight.Light))
            texts_layout.addWidget(metric)

            value = QLabel(f"{metric_data[i]}")
            value.setFont(QFont('Geist Mono', 8))
            texts_layout.addWidget(value)

            self.create_horizontal_line(metric_layout, 300)
            metric_layout.setContentsMargins(0, 0, 0, 0)
            self.bottom_left_layout.addWidget(metric_widget)

        self.bottom_left_layout.addStretch(0)

        self.create_line_spacer(self.bottom_layout, 250)

        self.bottom_right_section = QWidget()
        self.bottom_right_layout = QVBoxLayout()
        self.bottom_right_section.setLayout(self.bottom_right_layout)
        self.bottom_layout.addWidget(self.bottom_right_section)

        graph = BarChartWidget(self.ticker)

        consensus_section = QWidget()
        consensus_layout = QHBoxLayout()

        consensus_label = QLabel(f"Analyst Consensus: ")
        consensus_label.setFont(QFont('Inter', 15))
        consensus_layout.addWidget(consensus_label)
        consensus_section.setLayout(consensus_layout)

        consensus_value = QLabel(f"{graph.analyst_consensus}")
        consensus_value.setStyleSheet(f"color: {graph.analyst_consensus_color};")
        consensus_value.setFont(QFont('Inter', 15, QFont.Weight.Bold))
        consensus_layout.addWidget(consensus_value)
        self.bottom_right_layout.addWidget(consensus_section)

        
        self.bottom_right_layout.addWidget(graph)
        self.bottom_right_layout.addStretch(0)

        self.stock_info_layout_left.addWidget(self.bottom_section)
        

    def create_stock_info_section_right(self):
        """
        Creates the right section with the stock chart.
        """
        self.stock_info_section_right = QWidget()
        self.stock_info_layout_right = QHBoxLayout()
        self.stock_info_section_right.setFixedWidth(650)
        self.stock_info_layout_right.setContentsMargins(0, 0, 0, 0)
        self.stock_info_section_right.setLayout(self.stock_info_layout_right)
        self.stock_info_layout.addWidget(self.stock_info_section_right)
        
        data = yf.download(self.ticker, period="1y", interval="1d")
        df = data.reset_index()
        df['date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df["open"] = df["Open"]
        df["high"] = df["High"]
        df["low"] = df["Low"]
        df["close"] = df["Close"]
        df["volume"] = df["Volume"]
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.drop(df.index[0]).reset_index(drop=True)
        df = df.reset_index(drop=True)
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df.to_csv("graph.csv", index=False)
        graph_df = pd.read_csv("graph.csv")

        self.chart = QtChart(self.stock_info_section_right, toolbox=True)
        self.chart.layout(background_color="#121212")
        self.chart.candle_style(up_color='#14AE5C', down_color='#F24822')
        self.chart.watermark("Investmate")
        self.chart.topbar.switcher(
        'timeframe',
        ('1d', '1w', '1mo', '1y', 'max'),
        default='max',
        func=self.on_timeframe_selection
    )
        self.chart.set(graph_df)
        self.stock_info_layout_right.addWidget(self.chart.get_webview())

    def onLoadFinished(self):
        """
        Callback when the chart finishes loading.
        """
        print("Chart loaded successfully")

    def updateData(self, timeframe):
        """
        Updates chart data based on selected timeframe.
        """
        if timeframe == "1d":
            data = yf.download(self.ticker, period="1d", interval="15m")
            data.to_csv("unedited.csv", index=False)
        elif timeframe == "1w":
            return yf.download(self.ticker, period="7d", interval="30m")
        else:
            return yf.download(self.ticker, period=timeframe, interval="1d")

    def on_timeframe_selection(self, timeframe):
        """
        Handles timeframe selection for the chart.
        """
        if os.path.exists('graph.csv'):
            os.remove('graph.csv')
            data = self.updateData(timeframe)
            df = data.reset_index()
            df['date'] = df['Date'].dt.strftime('%Y-%m-%d')
            df["open"] = df["Open"]
            df["high"] = df["High"]
            df["low"] = df["Low"]
            df["close"] = df["Close"]
            df["volume"] = df["Volume"]
            df = df[["date", "open", "high", "low", "close", "volume"]]
            df = df.drop(df.index[0]).reset_index(drop=True)
            df = df.reset_index(drop=True)
            df = df[["date", "open", "high", "low", "close", "volume"]]
            df.to_csv("graph.csv", index=False)
            graph_df = pd.read_csv("graph.csv")
            self.chart.set(graph_df)

        else:
            print("File not found")
        

    def create_stock_info_section(self):
        """
        Creates the main stock info section with left and right parts.
        """
        self.stock_info_section = QWidget()
        self.stock_info_section.setFixedHeight(650)
        self.stock_info_layout = QHBoxLayout()
        self.stock_info_layout.setContentsMargins(0, 0, 0, 0)

        self.stock_info_section.setLayout(self.stock_info_layout)
        self.stock_container_layout.addWidget(self.stock_info_section)

        self.create_stock_info_section_left()
        self.create_line_spacer(self.stock_info_layout, 1000)
        self.create_stock_info_section_right()

    def create_overview_section(self):
        """
        Creates the overview section with company description.
        """
        self.overview_section = QWidget()
        self.overview_section.setFixedHeight(300)
        self.overview_layout = QVBoxLayout()
        self.overview_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_section.setLayout(self.overview_layout)
        self.stock_container_layout.addWidget(self.overview_section)

        overview_label = QLabel("Overview")
        overview_label.setFont(QFont('Inter', 25))
        self.overview_layout.addWidget(overview_label)

        self.overview_layout.addSpacing(10)

        overview_content = QLabel(self.description)
        overview_content.setWordWrap(True)
        overview_content.setFont(QFont('Inter', 15, QFont.Weight.Light))
        self.overview_layout.addWidget(overview_content)

        self.overview_layout.addStretch(0)

    def create_financials_section(self):
        """
        Creates the financials section with recent filings.
        """
        self.stock_container_layout.addSpacing(20)

        financials_label = QLabel("Financials")
        financials_label.setFont(QFont('Inter', 25))
        self.stock_container_layout.addWidget(financials_label)

        self.stock_container_layout.addSpacing(20)

        finnhub_api_key = os.getenv('FINNHUB_API_KEY')
        response = requests.get(f"https://finnhub.io/api/v1/stock/filings?symbol={self.ticker}&token={finnhub_api_key}")
        data = response.json()

        for record in data[:20]:
            financial_widget = QPushButton()
            financial_widget.setStyleSheet("""
                QPushButton {
                    background-color: #171B18;
                    border: none;
                    border-radius: 7px;
                }
                                           
                QPushButton:hover {
                    background-color: #777777;
                }
            """)
            financial_layout = QHBoxLayout()
            financial_layout.setContentsMargins(20, 5, 20, 5)
            financial_widget.setLayout(financial_layout)
            financial_widget.setFixedHeight(100)
            financial_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            financial_widget.clicked.connect(lambda _, url=record['filingUrl']: QDesktopServices.openUrl(QUrl(url)))
            

            title = QLabel(f"{record['form']}")
            title.setStyleSheet("background-color: none;")
            title.setFont(QFont('Geist Mono', 15, QFont.Weight.Bold))
            financial_layout.addWidget(title)

            financial_layout.addStretch(0)

            value = QLabel(f"{record['filedDate'].replace('-', '/')}")
            value.setStyleSheet("background-color: none;")
            value.setFont(QFont('Geist Mono', 10))
            financial_layout.addWidget(value)

            self.create_horizontal_line(self.stock_info_layout)

            self.stock_container_layout.addWidget(financial_widget)
        

    def run(self):
        """
        Initializes and runs the stock screen UI.
        """
        self.init_ui()
        self.create_stock_info_section()
        self.create_overview_section()
        self.create_financials_section()

        self.stock_container_layout.addStretch(0)