import re
import pymysql
import urllib.request, urllib.error
import json
import multiprocessing
import requests
from bs4 import BeautifulSoup
import time
import queue


'''
数据库标准说明：
MySQL型数据库
data库中climate表存放气象数据，users表存放用户数据
climate:max_temperature INT,min_temperature INT,city TEXT,year INT,month INT,day INT,weather TEXT,wind_direction TEXT,wind_strength TEXT
users:user_name TEXT,password TEXT,identity INT
'''

'''
集成函数说明(使用c++描述)：
1.void update(string ct,int startYear,int startMonth,int endYear,int endMonth):
    参数说明：传入参数含义依次为：城市名字，开始年，开始月，结束年，结束月。
    功能说明：实现数据库数据增加：某城市从[(startYear,startMonth)-->(endYear,endMonth)]的气象数据更新
2.void fetchData(string ct,int startYear,int startMonth,int endYear,int endMonth)
    参数说明：传入参数含义依次为：城市名字，开始年，开始月，结束年，结束月。
    应用场景说明：每次Qt端需要查询某个界面的数据即可调用这个函数
    功能说明：检[(startYear,startMonth)-->(endYear,endMonth)]漏，如果没有就调用更新函数。
'''

'''
连接数据库
conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='zhoujin@MySQL',
    charset='utf8'
)
'''


urlFirst = "https://lishi.tianqi.com/"
urlThirdOfDate = "/"
urlFinal = ".html"
cityList = {"长沙": "changsha", "武汉": "wuhan", "北京": "beijing", "杭州": "hangzhou", "上海": "shanghai",
            "南京": "nanjing"}
findLinkDate = re.compile(r'<div class="th200">(.*?)</div>')
findDataEach = re.compile(r'<div class="th140">(.*?)</div>')
findLinkIP=re.compile(r'<td class="table-ip">(.*?)</td>')
findLinkPort=re.compile(r'<td class="table-port">(.*?)</td>')
dateMax = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31, 20: 29}
failyear=queue.Queue()
failmonth=queue.Queue()

def getURL(address, year, month):
    url = urlFirst
    url += cityList[address]
    url += urlThirdOfDate
    url += str(year)
    if (month < 10):
        url += '0' + str(month)
    else:
        url += str(month)
    url += urlFinal
    return url


def askURL(url):
    head = {
        "User-Agent": "Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome / 80.0.3987.122  Safari / 537.36"
    }
    request = urllib.request.Request(url, headers=head)
    html = ""
    try:
        response = urllib.request.urlopen(request)
        html = response.read().decode("utf-8")
    except urllib.error.URLError as e:
        if hasattr(e, "code"):
            print(e.code)
        if hasattr(e, "reason"):
            print(e.reason)
    return html


def toint(s):
    if (s[0] == '0'):
        return int(s[1])
    return int(s)


def get_data(url, city, year, month):
    html = askURL(url)
    soup = BeautifulSoup(html, "html.parser")
    yc = 0
    while yc<=10:
        if soup.find_all('ul', class_="thrui").__len__()!=0:
            break
        else:
            print(city,":",year,".",month,"的数据获取异常。正在重试，请稍等...",end='')
            print()
            time.sleep(1)
            yc+=2
            html = askURL(url)
            soup = BeautifulSoup(html, "html.parser")
    if yc>=10:
        failyear.put(year)
        failmonth.put(month)
        return False
    for item in soup.find_all('ul', class_="thrui"):
        item = str(item)
        link = re.findall(findLinkDate, item)
        datas = re.findall(findDataEach, item)
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='zhoujin@MySQL',
            charset='utf8',
            database="data"
        )
        cursor = conn.cursor()
        sql = "INSERT INTO climate(max_temperature, min_temperature,city,year,month,day,weather,wind_direction,wind_strength) VALUES (%s, %s,\'%s\',%s,%s,%s,\'%s\',\'%s\',\'%s\')"
        dats = []
        for i in range(len(link)):
            datum = []
            datum.append(link[i])
            for j in range(4):
                datum.append(datas[i * 4 + j])
            eachDatum = (int(datum[1][:len(datum[1]) - 1]), int(datum[2][:len(datum[2]) - 1]), city, year, month,
                         toint(datum[0][8:10]), datum[3], datum[4].split()[0], datum[4].split()[1])
            dats.append(eachDatum)
            request = sql % eachDatum
            cursor.execute(request)
            conn.commit()
        cursor.close()
        conn.close()
    return True

# 提供接口：update()，输入：城市，起始日期，终止日期。

def update(ct,startYear,endYear,startMonth,endMonth):
    for year in range(startYear, endYear + 1):
        if year == startYear:
            for month in range(startMonth,13):
                get_data(getURL(ct, year, month), ct, year, month)
        elif year == endYear:
            for month in range(1,endMonth+1):
                get_data(getURL(ct, year, month), ct, year, month)
        else:
            for month in range(1,13):
                get_data(getURL(ct, year, month), ct, year, month)

def whetherhas(ct,year,month):
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='zhoujin@MySQL',
        charset='utf8',
        database="data"
    )
    cursor=conn.cursor()
    ans=False
    SQLSentence = "select * from climate"
    cursor.execute(SQLSentence)
    myResult=cursor.fetchall()
    for i in range(myResult.__len__()):
        if myResult[i][2] == ct and myResult[i][3] == year and myResult[i][4]==month:
            ans=True
            break
    cursor.close()
    conn.close()
    return ans

def fetchData(ct,startYear,endYear,startMonth,endMonth):
    for year in range(startYear,endYear+1):
        if year == startYear:
            for month in range(startMonth, 13):
                a=True
                if whetherhas(ct,year,month) == False:
                    a=get_data(getURL(ct, year, month), ct, year, month)
                if a:
                    print(ct,' ',year,month,"ok")
                    time.sleep(1)
        elif year == endYear:
            for month in range(1, endMonth + 1):
                a = True
                if whetherhas(ct, year, month) == False:
                    a = get_data(getURL(ct, year, month), ct, year, month)
                if a:
                    print(ct, ' ', year, month, "ok")
                    time.sleep(1)
        else:
            for month in range(1, 13):
                a = True
                if whetherhas(ct, year, month) == False:
                    a = get_data(getURL(ct, year, month), ct, year, month)
                if a:
                    print(ct, ' ', year, month, "ok")
                    time.sleep(1)

def get_proxy_list():
    #获取代理ip
    head = {
        "User-Agent": "Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome / 80.0.3987.122  Safari / 537.36"
    }
    url="https://proxycompass.com/cn/free-proxy/"


if __name__ == '__main__':
    '''
    n=int(input('times:'))
    for i in range(n):
        city=input("city:")
        syear=int(input('syear:'))
        smonth=int(input('smonth:'))
        eyear = int(input('eyear:'))
        emonth = int(input('emonth:'))
        fetchData(city,syear,eyear,smonth,emonth)
        print("City ",city,"'s data from",syear,".",smonth,"to",eyear,".",emonth,end='')
        print()
    '''
    '''
    city="武汉"
    syear=2012
    smonth=7
    eyear=2015
    emonth=6
    fetchData(city,syear,eyear,smonth,emonth)
    while failyear.empty() == False:
        yearnow=failyear.get()
        monthnow=failmonth.get()
        fetchData(city,yearnow,yearnow,monthnow,monthnow)
    '''
    get_proxy_list()