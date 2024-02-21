# frontier-monitor access class
import re
import sys
import json
import traceback
import requests
import urllib.request
from contextlib import closing

class SFComWeb:
    def __init__(self, sfmonip, userid, passwd):
        #session id
        self.session = None
        self.sessionid = None
        self.sfmonip = sfmonip
        self.userid = userid
        self.passwd = passwd

    ##--GetWeb--###########
    def getpvweb(self, url):
        #print(url, file=sys.stderr)
        req = urllib.request.Request(url)
        with closing(urllib.request.urlopen(req)) as res:
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
        if self.sessionid is not None:
            return self.sessionid
        url = 'https://www.frontier-monitor.com/permsite/D0000'
        params = {
            'actionId': 'LOGIN',
            'loginId': self.userid,
            'password': self.passwd,
        }
        try:
            self.session = requests.session()
            before_login = self.session.get(url)
            #print('before_status:' + str(before_login.status_code))
            jsessid = before_login.cookies.get('JSESSIONID')
            #print(jsessid)
            after_login = self.session.post(url + ';jsessionid=' + jsessid, data=params)
            #print('login_status:' + str(after_login.status_code))
            #print(after_login.text)
            mobj = re.search(r'input value=.*name="pmsessionid"', after_login.text)
            if mobj is None:
                self.sessionid = None
                print('login status:' + str(after_login.status_code))
                print(re.sub(re.compile('<.*?>', re.MULTILINE | re.DOTALL), '', after_login.text))
                print('login error:' + self.userid)
            else:
                self.sessionid = mobj.group().split('"')[1]
        except Exception as e:
            print(list(traceback.TracebackException.from_exception(e).format()), file=sys.stderr)
        return self.sessionid

    def getsfweb(self):
        # retry 3
        for num in range(3):
            try:
                sid = self.getSession()
                if sid is None:
                    continue
                url = 'https://www.frontier-monitor.com/permsite/D0100?pmsessionid=' + sid + '&selectItem=1'
                #print(url, file=sys.stderr)
                st = self.session.get(url)
                return st.text
            except Exception as e:
                print(list(traceback.TracebackException.from_exception(e).format()), file=sys.stderr)
        print('retry out', flush=True)
        return None

    def getpvkwh(self, result, idx):
        if result is None:
            return None
        if result in '[E004]':
            return None
        mobj = re.search(r'class="whList".*accesskey="1"', result)
        if mobj is None:
            print(result, flush=True)
            return None
        kwhs = mobj.group().split('/')
        if len(kwhs) < idx:
            return None
        rmstr = 'kW<' if idx == 3 else 'kWh<'
        return re.sub('^.*br>', '', kwhs[idx]).replace(rmstr, '').strip()

    def getpvval(self, res, idx):
        kwh = self.getpvkwh(res, 0)
        if kwh is None:
            self.sessionid = None
            return None
        return int(float(kwh) * 1000)

