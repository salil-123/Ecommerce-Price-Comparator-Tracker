from PyQt5 import uic,QtWidgets,QtGui
from PyQt5.Qt import Qt as QT
import numpy as np
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PyQt5.QtChart import QChart, QChartView, QValueAxis, QBarCategoryAxis, QBarSet, QBarSeries
from bs4 import BeautifulSoup
import requests
from difflib import get_close_matches
import webbrowser
from collections import defaultdict
import random
import sys
import pyqtgraph as pg

from smtplib import SMTP
from threading import Timer


form_class = uic.loadUiType("project.ui")[0]
        
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
        
class MainProject(QtWidgets.QMainWindow,form_class):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.showFullScreen()
        self.flip_link='https://www.flipkart.com'
        self.flip_review="0"
        self.flip_price='Product not available'
        self.flip_rating="0"
        self.amzn_link='https://www.amazon.in'
        self.amzn_review="0"
        self.amzn_price='Product not available'
        self.amzn_rating="0"
        self.pushButton.clicked.connect(self.find)
        self.pushButton_2.clicked.connect(self.visit_amzn)
        self.pushButton_3.clicked.connect(self.visit_flip)
        self.pushButton_4.clicked.connect(self.send_mail)
        with open('history.txt', 'r') as f:
            self.options = f.read().split('\n')[:3]
        self.comboBox.addItems(self.options)
        #self.comboBox.currentIndexChanged.connect(self.onselect)
        self.y1 = [0, 0, 0]
        self.y2 = [0, 0, 0]
        self.relativePrice_AMZN=0
        self.relativePrice_FLIP=0
        self.relativeReview_AMZN=0
        self.relativeReview_FLIP=0
        self.sanitized_amzn_price=''
        self.sanitized_flip_price=''
        self.minPrice=999999.0;

        self.setWindowTitle(QCoreApplication.translate("MainWindow", u"Price Comparison & Tracking Engine", None))
        
    def onselect(self, i):
        if not self.executed:
            m = self.comboBox.currentText()
            self.searchBox.setText(m)
            print("hello")
            self.pushButton.click()
            self.executed = True
            self.comboBox.currentIndexChanged.disconnect(self.onselect)
        
    def find(self):
        #clean input
        self.product = self.searchBox.text()
        self.product_arr = self.product.split()
        self.n = 1
        self.key = ""
        for word in self.product_arr:
            if self.n == 1:
                self.key = self.key + str(word)
                self.n += 1

            else:
                self.key = self.key + '+' + str(word)
        
        #scrape
        self.price_flipkart(self.key)
        self.price_amzn(self.key)
        
        #clean datapoints and set
        self.sanitized_amzn_price=self.amzn_price.replace(',','')
        self.sanitized_flip_price=self.flip_price.replace(',','')
        if self.is_float(self.sanitized_amzn_price) and self.is_float(self.sanitized_flip_price):
            self.relativePrice_AMZN=(float(self.sanitized_amzn_price)/float(self.sanitized_flip_price))*3
            self.relativePrice_FLIP=(float(self.sanitized_flip_price)/float(self.sanitized_amzn_price))*3
            if self.relativePrice_AMZN>5:
                self.relativePrice_AMZN=5
            if self.relativePrice_FLIP>5:
                self.relativePrice_FLIP=5
            if self.relativePrice_AMZN<0.5:
                self.relativePrice_AMZN=0.5
            if self.relativePrice_FLIP<0.5:
                self.relativePrice_FLIP=0.5
                
        if self.is_float(self.amzn_review) and self.is_float(self.flip_review):
            self.relativeReview_AMZN=(float(self.amzn_review)/float(self.flip_review))*3
            self.relativeReview_FLIP=(float(self.flip_review)/float(self.amzn_review))*3
            if self.relativeReview_AMZN>5:
                self.relativeReview_AMZN=5
            if self.relativeReview_FLIP>5:
                self.relativeReview_FLIP=5
            if self.relativeReview_AMZN<0.5:
                self.relativeReview_AMZN=0.5
            if self.relativeReview_FLIP<0.5:
                self.relativeReview_FLIP=0.5
                
        
        if self.is_float(self.sanitized_amzn_price):
            if self.is_float(self.sanitized_flip_price):
                if float(self.sanitized_amzn_price) < float(self.sanitized_flip_price):
                    self.minPrice= float(self.sanitized_amzn_price)
                if float(self.sanitized_amzn_price) >= float(self.sanitized_flip_price):
                    self.minPrice= float(self.sanitized_flip_price)
            else:
                self.minPrice= float(self.sanitized_amzn_price)
        elif self.is_float(self.sanitized_flip_price):
            self.minPrice= float(self.sanitized_flip_price)
            
        self.y1 = [self.relativePrice_AMZN, float(self.amzn_rating), self.relativeReview_AMZN]
        self.y2 = [self.relativePrice_FLIP, float(self.flip_rating), self.relativeReview_FLIP]
        
        #plot graph
        x1 = [0.8, 1.8, 2.8]
        x2 = [1.2, 2.2, 3.2]
        bargraph = pg.BarGraphItem(x = x1, height = self.y1, width = 0.4, brush ='g', name="Amazon")
        bargraph2 = pg.BarGraphItem(x = x2, height = self.y2, width = 0.4, brush ='r', name="Flipkart")
        self.widget.clear()
        self.widget.addLegend(offset=(0,20))
        self.widget.addItem(bargraph)
        self.widget.addItem(bargraph2)
        self.widget.setLimits(xMin=0,xMax=4,yMin=0,yMax=7)
        self.widget.setYRange(0,7, padding=0, update=True)
        self.widget.setXRange(0,4, padding=0, update=True)
        self.widget.setMouseEnabled(x=False, y=False)
        self.widget.setTitle('Amazon vs Flipkart Comparison')
        self.widget.setLabel('bottom', 'Key Points')
        self.widget.setLabel('left', 'Relative Stats')
        self.widget.hideButtons()
        self.graphlabels = [(1,'Price'),(2,'Rating'),(3,'Reviews')]
        ax=self.widget.getAxis('bottom')
        ax.setTicks([self.graphlabels])
        
        self.comboBox.clear()
        with open('history.txt', 'r') as f:
            self.original_text = f.read()
        self.new_text = self.product
        self.text = self.new_text +"\n"+ self.original_text
        with open('history.txt', 'w') as f:
            f.write(self.text)
        with open('history.txt', 'r') as f:
            self.options = f.read().split('\n')[:3]
        self.comboBox.addItems(self.options)
            
    def is_float(self,string):
        try:
            float(string)
            return True
        except:
            return False
    
    def price_flipkart(self, key):
        url_flip = 'https://www.flipkart.com/search?q=' + str(
            key) + '&marketplace=FLIPKART&otracker=start&as-show=on&as=off'
        map = defaultdict(list)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        source_code = requests.get(url_flip, headers=self.headers)
        soup = BeautifulSoup(source_code.text, "html.parser")
        self.opt_title_flip = ""
        home = 'https://www.flipkart.com'
        for block in soup.find_all('div', {'class': '_2kHMtA'}):
            title, price, link = None, 'Currently Unavailable', None
            for heading in block.find_all('div', {'class': '_4rR01T'}):
                title = heading.text
            for p in block.find_all('div', {'class': '_30jeq3 _1_WHN1'}):
                price = p.text[1:]
            for l in block.find_all('a', {'class': '_1fQZEK'}):
                link = home + l.get('href')
            map[title] = [price, link]

        user_input = self.searchBox.text()
        self.matches_flip = get_close_matches(user_input, map.keys(), 20, 0.1)
        self.looktable_flip = {}
        for title in self.matches_flip:
            self.looktable_flip[title] = map[title]

        try:
            self.label_6.setText(QCoreApplication.translate("MainWindow", self.matches_flip[0], None))
            self.flip_price=self.looktable_flip[self.matches_flip[0]][0] + '.00'
            self.flip_link = self.looktable_flip[self.matches_flip[0]][1]
            self.getFlipkartDetails(self.flip_link) 
        except IndexError:
            self.label_6.setText(QCoreApplication.translate("MainWindow", 'Product not available', None))
            self.flip_price='Product not available'
            self.flip_link='https://www.flipkart.com'
        self.label_8.setText(QCoreApplication.translate("MainWindow", self.flip_price, None))

    def price_amzn(self, key):
        url_amzn = 'https://www.amazon.in/s/ref=nb_sb_noss_2?url=search-alias%3Daps&field-keywords=' + str(key)

        # Faking the visit from a browser
        headers = {
            'authority': 'www.amazon.com',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'dnt': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-dest': 'document',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        map = defaultdict(list)
        home = 'https://www.amazon.in'
        proxies_list = ["128.199.109.241:8080", "113.53.230.195:3128", "125.141.200.53:80", "125.141.200.14:80",
                        "128.199.200.112:138", "149.56.123.99:3128", "128.199.200.112:80", "125.141.200.39:80",
                        "134.213.29.202:4444"]
        proxies = {'https': random.choice(proxies_list)}
        source_code = requests.get(url_amzn, headers=headers)
        plain_text = source_code.text
        self.opt_title = ""
        self.soup = BeautifulSoup(plain_text, "html.parser")
        # print(self.soup)
        # print(self.soup.find_all('div', {'class': 'sg-col-inner'}))
        for html in self.soup.find_all('div', {'class': 'sg-col-inner'}):
            title, link,price = None, None,None
            for heading in html.find_all('span', {'class': 'a-size-medium a-color-base a-text-normal'}):
                title = heading.text
            for p in html.find_all('span', {'class': 'a-price-whole'}):
                price = p.text
            for l in html.find_all('a', {'class': 'a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal'}):
                link = home + l.get('href')
            if title and link:
                map[title] = [price, link]
        user_input = self.searchBox.text()
        self.matches_amzn = get_close_matches(user_input, list(map.keys()), 20, 0.01)
        self.looktable_amzn = {}
        for title in self.matches_amzn:
            self.looktable_amzn[title] = map[title]
            
    
        try:
            self.label_2.setText(QCoreApplication.translate("MainWindow", self.matches_amzn[0], None))
            self.amzn_price=self.looktable_amzn[self.matches_amzn[0]][0] + '.00'
            self.amzn_link = self.looktable_amzn[self.matches_amzn[0]][1]
            self.getAmazonDetails(self.amzn_link) 
        except IndexError:
            self.label_2.setText(QCoreApplication.translate("MainWindow", 'Product not available', None))
            self.amzn_price='Product not available'
            self.amzn_link='https://www.amazon.in'
        self.label_4.setText(QCoreApplication.translate("MainWindow", self.amzn_price, None))
            
    def getAmazonDetails(self,URL):
        HEADERS = ({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64)','Accept-Language': 'en-US, en;q=0.5'})
        webpage = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(webpage.content, "lxml")
        try:
            self.amzn_rating = soup.find("i", attrs={'class': 'a-icon a-icon-star a-star-4-5'}).string.strip().replace(',', ''). split()[0]
            self.amzn_review = soup.find("span", attrs={'id': 'acrCustomerReviewText'}).string.strip().replace(',', ''). split()[0]
        except AttributeError:
            self.amzn_rating = "0"
            self.amzn_review = "0"
            
    def getFlipkartDetails(self,URL):
        HEADERS = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'})
        webpage = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(webpage.content, "html.parser")
        try:
            self.flip_rating = soup.find("div", attrs={'class': '_3LWZlK'}).text.strip().replace(',', ''). split()[0]
            self.flip_review = soup.find("span", attrs={'class': '_2_R_DZ'}).text.strip().replace(',', ''). split()[0]
        except AttributeError:
            self.flip_rating = "0"
            self.flip_review = "0"
        
    def visit_amzn(self):
        webbrowser.open(self.amzn_link)

    def visit_flip(self):
        webbrowser.open(self.flip_link)
    
    def send_mail(self):
        SMTP_SERVER="smtp.gmail.com"
        PORT=587
        self.EMAIL_ID="salilsandeshgujar@gmail.com"
        PASSWORD="dhiuzbsxmifgpgtv"
        self.server=SMTP(SMTP_SERVER,PORT)
        self.server.starttls()
        self.server.login(self.EMAIL_ID,PASSWORD)
        
        #self.email()
        print("starting Automatic Email Notification")
        rt = RepeatedTimer(60, self.email)
        
        
    def email(self):
        self.ap=0
        self.fp=0
        self.price_flipkart(self.key)
        self.price_amzn(self.key)
        self.sanitized_amzn_price=self.amzn_price.replace(',','')
        self.sanitized_flip_price=self.flip_price.replace(',','')
        if self.is_float(self.sanitized_amzn_price):
            if self.is_float(self.sanitized_flip_price):
                if float(self.sanitized_amzn_price) < float(self.sanitized_flip_price):
                    self.minPrice= float(self.sanitized_amzn_price)
                    self.ap=1
                if float(self.sanitized_amzn_price) >= float(self.sanitized_flip_price):
                    self.minPrice= float(self.sanitized_flip_price)
                    self.fp=1
            else:
                self.minPrice= float(self.sanitized_amzn_price)
                self.ap=1
        elif self.is_float(self.sanitized_flip_price):
            self.minPrice= float(self.sanitized_flip_price)
            self.fp=1
        
        if self.is_float(self.textEdit.toPlainText()):
            if self.minPrice < float(self.textEdit.toPlainText()):
                if self.fp==1:
                    subject="Buy now!"
                    body="This product is now in your desired price range on amazon \n"+self.amzn_link
                    msg=f"Subject:{subject}\n\n{body}"
                elif self.ap==1:
                    subject="Buy now!"
                    body="This product is now in your desired price range on flipkart \n!"+self.flip_link
                    msg=f"Subject:{subject}\n\n{body}"
            else:
                subject="No dice."
                body="This product still isn't in your desired price range"
                msg=f"Subject:{subject}\n\n{body}"
            self.server.sendmail(self.EMAIL_ID,self.textEdit_2.toPlainText(),msg)
            print('sent mail')
        
    
        
        
        
if __name__=="__main__":
    app = QtWidgets.QApplication(sys.argv)
    MyWindow = MainProject(None)
    MyWindow.show()
    app.exec_()
    sys.exit()
