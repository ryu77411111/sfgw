# frontier-monitor access class
import re
import sys
import json
import traceback
import requests
import urllib.request
from datetime import datetime

class SFComWeb:
    def __init__(self, sfmonip, userid, passwd):
        #session id
        self.session = None
        self.sfmonip = sfmonip
        self.userid = userid
        self.passwd = passwd

    def gettoday(self):
        now = datetime.now()
        return f'{now:%Y/%m/%d}'.split('/')

    ##--GetWeb--###########
    def getpvweb(self, url):
        #print(url, file=sys.stderr)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            result = res.read().decode()
            mobj = re.search(r'{.*}', result)
            if mobj is None:
                return None
            jobj = json.loads(mobj.group())
            #print(jobj['added_power'] + jobj['added_sellpower'] + jobj['added_buypower'])
            return jobj

    ##--GetPV--###########
    def tow(self, val):
        if val is None:
            return None
        try:
            num = float(val)
            return round(num)
        except ValueError:
            print(val)
        return 

    def getpvw(self):
        url = f'http://{self.sfmonip}/GetMonitoringData.cgi'
        try:
            result = self.getpvweb(url)
            if result is None:
                return None
            return self.tow(result['added_power'])
        except Exception as e:
            print(list(traceback.TracebackException.from_exception(e).format())[-1] + url, file=sys.stderr)
            return None

    ##--GetSession--###########
    def getSession(self):
        if self.session is not None:
            return self.session

        url = 'https://www.frontier-monitor.com/persite'
        params = {
            'actionId': 'LOGIN',
            'screenId': 'C0000',
            'loginId': self.userid,
            'password': self.passwd,
            'httpsurl': url,
        }
        try:
            session = requests.session()
            login = session.post(url + '/top', data=params)
            #print('login_status:' + str(login.status_code))
            if 'GlobalNavi' in login.text:
                self.session = session
                return self.session
            else:
                print("login error", file=sys.stderr)
        except Exception as e:
            print(list(traceback.TracebackException.from_exception(e).format()), file=sys.stderr)
        return None

    def getsfweb(self, day=None):
        ymd = self.gettoday() if day is None else day.split('/')
        url = 'https://www.frontier-monitor.com/persite/C0300'
        params = {
            'actionId': 'AJ_RELOAD',
            'param1': '1',
            'dateY': ymd[0],
            'dateM': ymd[1],
            'dateD': ymd[2],
            'dateH': '0',
            'eventflg': '0',
        }
        # retry 3
        for num in range(3):
            try:
                if self.getSession() is None:
                    continue
                result = self.session.post(url, data=params)
                #print(result.text, file=sys.stderr)
                jobj = json.loads(result.text)
                return jobj
            except Exception as e:
                self.session = None
                print(list(traceback.TracebackException.from_exception(e).format()), file=sys.stderr)
        print('retry out', flush=True)
        return None

    def tostr(self, json):
        if json is None:
            return None
        try:
            return f"{json['hatsudenkwh']} {json['uttakwh']} {json['kattakwh']} {json['shohikwh']} {json['hatsudenkwmax']}"
        except Exception as e:
            return ''

    def getpvkwh(self, json):
        if json is None:
            return None
        if 'hatsudenkwh' not in json:
            return None
        return json['hatsudenkwh']

    def getpvval(self, json):
        kwh = self.getpvkwh(json)
        if kwh is None:
            self.session = None
            return None
        return int(float(kwh) * 1000)

