import time, sqlite3, hashlib, os, requests, json, folium
from bs4 import BeautifulSoup
from bokeh.plotting import figure, output_file, show


def requests_html(url):
    html = ''
    while html == '':
        try:
            html = requests.get(url)
        except:
            print('Connection refused by the server..')
            print('Let me sleep for 5 seconds')
            print('ZZzzzz...')
            time.sleep(5)
            print("Was a nice sleep, now let me continue...")

    return html


def counting():
    cursor = conn.execute("select max(InsertNo) from TablePM25")
    row = cursor.fetchone()
    if row[0] == None:
        return 0
    else:
        return int(row[0])


def get_color(PM25):
  if PM25 < 36:
    return 'green'
  elif PM25 < 54:
    return 'orange'
  elif PM25 < 71:
    return 'red'
  else:  
    return 'purple'


sites_conn = sqlite3.connect('PM25_Sites.sqlite')  # 建立資料庫連線，若不存在，則新建資料庫
sites_cursor = sites_conn.cursor()  # 建立 cursor 物件


sqlstr = '''
CREATE TABLE IF NOT EXISTS TableSites("no" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE ,"SiteName" TEXT NOT NULL UNIQUE,"country" TEXT NOT NULL ,"Latitude" REAL,"Longitude" REAL, "Address" TEXT )
'''

sites_cursor.execute(sqlstr)


url = 'https://data.epa.gov.tw/api/v1/aqx_p_07?format=json&api_key=9be7b239-557b-4c10-9775-78cadfc555e9'
# 讀取網頁原始碼
html = requests.get(url).text.encode('utf-8')

# 判斷網頁是否更新
new_md5 = hashlib.md5(html).hexdigest()
old_md5 = ""

# Sites
if os.path.exists('old_site_md5.txt'):
    with open('old_site_md5.txt', 'r') as f:
        old_md5 = f.read()
with open('old_site_md5.txt', 'w') as f:
    f.write(new_md5)


if old_md5 != new_md5:
    print("Sites資料已更新...")    
    sp=BeautifulSoup(html,'html.parser')

    jsondata = json.loads(sp.text)
    sites_conn.execute('delete from TableSites')
    sites_conn.commit()

    n=1
    for site in jsondata["records"]: 

        SiteName = site["SiteName"]
        country = site["County"]
        lon = site["TWD97Lon"]
        lat = site["TWD97Lat"]
        address = site["SiteAddress"]

        sqlstr="insert into TableSites values({},'{}','{}', {}, {}, '{}')" .format(n,SiteName,country, lat, lon, address)

        sites_cursor.execute(sqlstr)
        sites_conn.commit() # 主動更新
        n += 1
else:
  print("Sites資料未更新...") 

print('===================== PM25_Sites =====================')

sites_cursor = sites_conn.execute("select * from TableSites")
s_rows = sites_cursor.fetchall()

n = 1
for row in s_rows:
    print('{:>2} 站名:{}({})   Lat={}   Lon={}'.format(row[0], row[1], row[2], row[3], row[4]))

print('======================================================\n')


conn = sqlite3.connect('DataBasePM25.sqlite')  # 建立資料庫連線，若不存在，則新建資料庫
cursor = conn.cursor()  # 建立 cursor 物件

# 建立一個資料表(如果不存在)
sqlstr = '''
CREATE TABLE IF NOT EXISTS TablePM25 ("SiteName" TEXT NOT NULL, "country" TEXT NOT NULL  ,"PM25" INTEGER, "DataCreationDate" TEXT, "InsertNo" INTEGER, CONSTRAINT FUCK UNIQUE (SiteName, DataCreationDate))
'''
cursor.execute(sqlstr)

url = "https://data.epa.gov.tw/api/v1/aqx_p_02?format=json&api_key=9be7b239-557b-4c10-9775-78cadfc555e9"

# 讀取網頁原始碼
html = requests.get(url).text.encode('utf-8')

# 判斷網頁是否更新
new_md5 = hashlib.md5(html).hexdigest()
old_md5 = ""

# PM2.5
if os.path.exists('old_md5.txt'):
    with open('old_md5.txt', 'r') as f:
        old_md5 = f.read()
with open('old_md5.txt', 'w') as f:
    f.write(new_md5)

if new_md5 != old_md5:

    print('*** PM2.5資料已更新...')
    sp = BeautifulSoup(html, 'html.parser')

    jsondata = json.loads(sp.text)
    jsondata = jsondata['records']

    currentInsertNo = counting() + 1  # 找出currentInsertNo用的

    for site in jsondata:
        SiteName = site["Site"]
        country = site["county"]
        
        if site["PM25"] == "":
            PM25 = 0
        else:
            PM25 = int(site["PM25"])
        
        DataCreationDate = site["DataCreationDate"]
        
        if DataCreationDate[:4] != '2020':
          sqlstr = "insert into TablePM25 values('{}', '{}', {}, '{}', {})".format(SiteName, country, PM25, DataCreationDate, currentInsertNo)
          try:
            cursor.execute(sqlstr)
          except Exception as e:
            pass
          else:
            n += 1
          conn.commit()  # 主動更新

else:
    print('*** 資料未更新...')


currentInsertNo = counting()
print('*** currentInsertNo =', currentInsertNo)

cursor = conn.execute("select * from TablePM25 where InsertNo = {} ".format(currentInsertNo))
rows = cursor.fetchall()


print('======= PM2.5即時資訊({}) ======='.format(rows[0][3]))

n = 1
for row in rows:
    print('{:>2d} 站名:{}({})  PM2.5={:>2d}   '.format(n, row[0], row[1], row[2]), end='')
    
    if (row[2] < 36):
        print(" *** 綠 ***")
    elif (row[2] < 54):
        print(" *** 黃 ***")
    elif (row[2] < 71):
        print(" *** 紅 ***")
    else:
        print(" *** 紫 ***")

    ShitName = row[0]
    cursor = conn.execute("select * from TablePM25 where SiteName = '{}'".format(ShitName))
    five_rows = cursor.fetchall()

    idx = 0

    # 畫柱狀圖用的list
    t_list = []
    pm25_list = []
    color_list = []

    for five_row in reversed(five_rows):
      t_list.append(five_row[3])
      pm25_list.append(five_row[2])
      if (row[2] < 36):
          c = 'green'
      elif (row[2] < 54):
          c = 'orange'
      elif (row[2] < 71):
          c = 'red'
      else:
          c = 'purple'
      color_list.append(c)
      
      idx += 1
      if idx == 5:
        break
      
    output_file(ShitName+"_Recent5.html")

    pm25_list.reverse()
    t_list.reverse()
    color_list.reverse()

    p = figure(x_range=t_list, title=ShitName+"-Recent5")
    p.vbar(x=t_list, top=pm25_list, width=0.2, color=color_list)
    p.text(x=t_list, y=pm25_list, text=pm25_list)
    
    show(p)
    
    n += 1

map = folium.Map([23.973918, 120.979692], zoom_start=8)

for site in s_rows:
  link = folium.Html('<a href="http://www1.pu.edu.tw/~s1070334/python_class/HW6/{}_Recent5.html">{}</a>'.format(site[1], site[1]+'(' + str(rows[0][2]) + ')'), script=True)
  popup = folium.Popup(link, max_width=200)

  if (rows[0][2] < 36):
      c = 'green'
  elif (rows[0][2] < 54):
      c = 'orange'
  elif (rows[0][2] < 71):
      c = 'red'
  else:
      c = 'purple'

  mk = folium.Marker(location=[site[3], site[4]], icon=folium.Icon(color=c,icon='location-arror', prefix='fa'), popup = popup)

  map.add_child(mk)

map.save('[HW6]PM25_OSM.html')
print('*** Generated: ' + '[HW6]PM25_OSM.html');

conn.close()