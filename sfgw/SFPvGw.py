#!/usr/bin/python3

import re
import sys
import time
import socket
import binascii
import traceback
import SFComWeb
import SFCfg
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import closing

def receive_multi(sf):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', SFCfg.ECHONET_PORT))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(SFCfg.MULTI_ADDR) + socket.inet_aton(SFCfg.LOCAL_ADDR))

        inf = response_state_cmd('0000', '0ef001', '0ef001', '01', '73', 'd5', '02 027901 05ff01')
        print(getnow() + ' INF:[' + SFCfg.MULTI_ADDR + ']' + inf, flush=True)
        sock.sendto(binascii.unhexlify(inf), (SFCfg.MULTI_ADDR , SFCfg.ECHONET_PORT))

        while True:
            try:
                row, addr = sock.recvfrom(4096)
                hex = str(binascii.hexlify(row), 'utf-8')
                tid, seoj, deoj, esv, req = hex[4:8], hex[8:14], hex[14:20], hex[20:22], hex[22:]
                response_send(sf, sock, addr, tid, seoj, deoj, esv, req)
            except Exception as e:
                msg = str(list(traceback.TracebackException.from_exception(e).format()))
                print(msg.replace('\\n', '\n'), flush=True)

def response_send(sf, sock, addr, tid, seoj, deoj, esv, req):
    opc = int(req[:2], 16)
    epclst = req[2:]
    #print(f'!!REQ({addr[0]},{deoj}:{esv}->' + req, flush=True)
    #要求毎に判定
    res = None
    if esv == '62': # 読出し要求
        #print(f'!!REQ({addr[0]},{deoj}:{esv}->' + epclst, flush=True)
        if deoj.startswith('05ff'):
            #コントローラ
            edt = response_edit05ff(addr, tid, seoj, deoj, opc, epclst)
            #print(f'ctrl-RES:{addr[0]},{deoj}:{esv}({opc})->' + edt, flush=True)
            res = response_state(tid, seoj, deoj, '72', opc, edt)
        elif deoj.startswith('0ef0'):
            #ノードプロファイル
            edt = response_edit0ef0(addr, tid, seoj, deoj, opc, epclst)
            #print(f'node-RES:{addr[0]},{deoj}:{esv}({opc})->' + edt, flush=True)
            res = response_state(tid, seoj, deoj, '72', opc, edt)
        elif deoj.startswith('0279'):
            #太陽光プロファイル
            edt = response_edit0279(sf, addr, tid, seoj, deoj, opc, epclst)
            #print(f'PV-RES:{addr[0]},{deoj}:{esv}({opc})->' + edt, flush=True)
            res = response_state(tid, seoj, deoj, '72', opc, edt)
        elif deoj.startswith('027d'):
            #蓄電池プロファイル
            res = None
        else:
            print(f'REQ({addr[0]}:{deoj},{esv}({opc})->' + epclst, flush=True)
            res = None
    elif esv == '63': # 通知要求
        res = response_edit_inf(addr, tid, seoj, deoj, opc, epclst)
        #print(f'INF({addr[0]}:{deoj},{esv}({opc})->' + res, flush=True)
        res = response_state(tid, seoj, deoj, '72', opc, res)
    elif esv == '73': # プロパティ値通知
        res = None
        #print('0ef0 EDT(' + esv + '):' + addr[0] + ',' + req, flush=True)
    else:
        res = None
        print('Unknown ESV:' + esv, flush=True)
    #応答／通知送信
    if res:
        #print(res)
        rb = binascii.unhexlify(res)
        sock.sendto(rb, (addr[0], SFCfg.ECHONET_PORT))

#通知
def response_edit_inf(addr, tid, seoj, deoj, opc, epclst):
    ofs = 0
    res = ''
    # INF
    for idx in range(opc):
        epc, pdc = epclst[ofs:ofs+2], int(epclst[ofs+2:ofs+4], 16)
        ofs += (4 + pdc)
        if epc == 'd5': # インスタンス変化
            res = response_epc(epc, '02 027901 0ef001')
        else:
            print('0ef0 INFREQ(' + epc + '):' + addr[0] + ',' + req, flush=True)
    # 戻り値
    return res

#コントローラ
def response_edit05ff(addr, tid, seoj, deoj, opc, epclst):
    ofs = 0
    res = ''
    # GET
    for idx in range(opc):
        epc, pdc = epclst[ofs:ofs+2], int(epclst[ofs+2:ofs+4], 16)
        ofs += (4 + pdc)
        if epc == '80': # 動作状態
            res += response_epc(epc, '30')
        elif epc == '81': # 設置場所
            res += response_epc(epc, '00')
        elif epc == '82': # Version
            res += response_epc(epc, '00004b00')
        elif epc == '83': # ノード識別番号
            res += response_epc(epc, f'{SFCfg.PV_NODEN:0<34}'[:34])
        elif epc == '88': # 異常発生状態
            res += response_epc(epc, '42')
        elif epc == '8a': # メーカーコード
            res += response_epc(epc, f'{SFCfg.PV_MAKER:0<6}'[:6])
        elif epc == 'd3': # 自node instance数
            res += response_epc(epc, '000002')
        elif epc == 'd4': # 自node class数
            res += response_epc(epc, '0003')
        elif epc == '9d': # map
            res += response_epc(epc, '03 808188')
        elif epc == '9e': # map
            res += response_epc(epc, '01 81')
        elif epc == '9f': # propaty map
            res += response_epc(epc, '08 80 81 82 88 8a 9d 9e 9f')
        else:
            res += response_epc(epc, '00')
            print('Unknown EPC:' + addr[0] + ',' + epc, flush=True)
    # 戻り値
    return res

#ノードプロファイル
def response_edit0ef0(addr, tid, seoj, deoj, opc, epclst):
    ofs = 0
    res = ''
    # GET
    for idx in range(opc):
        epc, pdc = epclst[ofs:ofs+2], int(epclst[ofs+2:ofs+4], 16)
        ofs += (4 + pdc)
        if epc == '80': # 動作状態
            res += response_epc(epc, '30')
        elif epc == '82': # Version
            res += response_epc(epc, '00004b00')
        elif epc == '83': # ノード識別番号
            res += response_epc(epc, f'{SFCfg.PV_NODEN:0<34}'[:34])
        elif epc == '88': # 異常発生状態
            res += response_epc(epc, '42')
        elif epc == '8a': # メーカーコード
            res += response_epc(epc, f'{SFCfg.PV_MAKER:0<6}'[:6])
        elif epc == '8d': # 製造番号
            res += response_epc(epc, f'{SFCfg.PV_LOTNO:0<24}'[:24])
        elif epc == 'bf': # 個体識別情報
            res += response_epc(epc, '003b')
        elif epc == 'd3': # 自node instance数
            res += response_epc(epc, '000002')
        elif epc == 'd4': # 自node class数
            res += response_epc(epc, '0003')
        elif epc == 'd6': # 自node instance
            res += response_epc(epc, '02 027901 05ff01')
        elif epc == 'd7': # 自node class
            res += response_epc(epc, '02 0279 0ef0')
        elif epc == '9d': # map
            res += response_epc(epc, '02 80 d5')
        elif epc == '9e': # map
            res += response_epc(epc, '01 bf')
        elif epc == '9f': # propaty map
            res += response_epc(epc, '0d 80 82 83 88 8a 8d 9d 9e 9f d3 d4 d6 d7')
        else:
            res += response_epc(epc, '00')
            print('Unknown EPC:' + epc, flush=True)
    # 戻り値
    return res

#太陽光プロファイル
def response_edit0279(sf, addr, tid, seoj, deoj, opc, epclst):
    ofs = 0
    res = ''
    # GET
    for idx in range(opc):
        epc, pdc = epclst[ofs:ofs+2], int(epclst[ofs+2:ofs+4], 16)
        ofs += (4 + pdc)
        if epc == '80': # 動作状態
            res += response_epc(epc, '30')
        elif epc == '81': # 設置場所
            res += response_epc(epc, '00')
        elif epc == '82': # Version
            res += response_epc(epc, '00004b00')
        elif epc == '83': # ノード識別番号
            res += response_epc(epc, f'{SFCfg.PV_NODEN:0<34}'[:34])
        elif epc == '86': # メーカー異常コード
            res += response_epc(epc, '00')
        elif epc == '88': # 異常発生状態
            res += response_epc(epc, '42')
        elif epc == '89': # 異常内容
            res += response_epc(epc, '0000')
        elif epc == '8a': # メーカーコード
            res += response_epc(epc, f'{SFCfg.PV_MAKER:0<6}'[:6])
        elif epc == '8c': # 商品コード
            res += response_epc(epc, f'{SFCfg.PV_PRDCT:0<24}'[:24])
        elif epc == '8d': # 製造番号
            res += response_epc(epc, f'{SFCfg.PV_LOTNO:0<24}'[:24])
        elif epc == '8e': # 製造年月日
            res += response_epc(epc, tohexymd(SFCfg.PVSET_YMD))
        elif epc == '93': # 遠隔操作設定
            res += response_epc(epc, '41')
        elif epc == '97': # 現在時刻
            res += response_epc(epc, getnowhexhm())
        elif epc == '98': # 現在年月日
            res += response_epc(epc, getnowhexymd())
        elif epc == '9a': # 積算運転時間
            dt = diffymd(SFCfg.PVSET_YMD)
            res += response_epc(epc, f'44 {dt:08x}')
        elif epc == '9d': # 状変map
            res += response_epc(epc, '04 80 81 88 b1')
        elif epc == '9e': # Set propaty map
            res += response_epc(epc, '08 81 93 97 98 a0 a1 a2 c1')
        elif epc == '9f': # Get propaty map
            #res += response_epc(epc, '1b e1 c1 81 83 00 40 01 00 41 41 83 00 01 03 03 02')
            res += response_epc(epc,  '22 6D 7D 1D 1B 18 00 01 02 43 41 01 00 01 03 02 02')
        elif epc == 'a0': # 出力制御設定１
            res += response_epc(epc, '64')
        elif epc == 'a1': # 出力制御設定２
            res += response_epc(epc, '0000')
        elif epc == 'a2': # 余剰買取制御機能設定
            res += response_epc(epc, '41')
        elif epc == 'b0': # 出力制御スケジュール
            res += response_epc(epc, f'{"":f<200}')
        elif epc == 'b1': # 次回アクセス日時
            res += response_epc(epc, 'ffffffff ffffff')
        elif epc == 'b2': # 余剰買取制御機能タイプ
            res += response_epc(epc, '41')
        elif epc == 'b3': # 
            print('0279 EPC:' + epc, flush=True)
            res += response_epc(epc, '00')
        elif epc == 'b4': # 上限クリップ設定値
            res += response_epc(epc, 'ffff')
        elif epc == 'c1': # FIT契約タイプ
            res += response_epc(epc, '43')
        elif epc == 'c2': # 自家消費タイプ
            res += response_epc(epc, '43')
        elif epc == 'c3': # 設備認定容量
            res += response_epc(epc, 'ffff')
        elif epc == 'c4': # 換算係数
            res += response_epc(epc, '01')
        elif epc == 'd0': # 系統連系状態
            res += response_epc(epc, '00')
        elif epc == 'd1': # 出力抑制状態
            res += response_epc(epc, '44')
        elif epc == 'e0': # 発電瞬時値
            pvw = sf.getpvw()
            val = f'{pvw:04x}' if pvw else '0000'
            res += response_epc(epc, val)
        elif epc == 'e1': # 発電積算値
            result = 0
            contents = sf.getsfweb()
            if contents:
                result = sf.getpvval(contents, 0)
                print(getnow() + ' 0279 EPC(' + epc + '):' + addr[0] + ',' + f'{result:08x}, {result}wh', flush=True)
            val = f'{result:08x}' if result else '00000000'
            res += response_epc(epc, val)
        elif epc == 'e5': # 発電電力制限設定１
            res += response_epc(epc, '64')
        elif epc == 'e8': # 定格発電電力値（系統連系時）
            res += response_epc(epc, f'{SFCfg.PVW_SPEC:04x}')
        elif epc == 'e9': # 定格発電電力値（独立時）
            res += response_epc(epc, f'{SFCfg.PVW_SPEC:04x}')
        else:
            res += response_epc(epc, '00')
            print('Unknown EPC:' + epc, flush=True)
    # 戻り値
    return res

def response_epc(epc, edt):
    edt = edt.replace(' ', '')
    #PDC 制御コマンド数
    pdc = f'{int(len(edt)/2):02x}'
    return epc + pdc + edt

def response_state(tid, seoj, deoj, esv, opc, res):
    if res is None:
        return None
    if len(res) < 1:
        return None
    #                     #   2      2       3       3      1      1
    format_echonet_lite = ['EHD', 'TID', 'SEOJ', 'DEOJ', 'ESV', 'OPC', 'RES']
    data_format = {
        format_echonet_lite[0]: '1081', #EHD 固定
        format_echonet_lite[1]: tid, #TID
        format_echonet_lite[2]: deoj, #SEOJ 送信元PV or Node
        format_echonet_lite[3]: seoj, #DEOJ 送信先
        format_echonet_lite[4]: esv, #ESV 71:書込応答,72:読出応答,73:通知
        format_echonet_lite[5]: f'{opc:02x}', #OPC 取得コマンド数
        format_echonet_lite[6]: res # レスポンス
    }
    frame = ''
    for key in format_echonet_lite:
        frame += data_format[key]
    return frame

def response_state_cmd(tid, seoj, deoj, opc, esv, epc, edt):
    edt = edt.replace(' ', '')
    #PDC 制御コマンド数
    pdc = f'{int(len(edt)/2):02x}'
    #                     #   2      2       3       3      1      1      1      1
    format_echonet_lite = ['EHD', 'TID', 'SEOJ', 'DEOJ', 'ESV', 'OPC', 'EPC', 'PDC', 'EDT']
    data_format = {
        format_echonet_lite[0]: '1081', #EHD 固定
        format_echonet_lite[1]: tid, #TID
        format_echonet_lite[2]: deoj, #SEOJ 送信元PV or Node
        format_echonet_lite[3]: seoj, #DEOJ 送信先
        format_echonet_lite[4]: esv, #ESV 71:書込応答,72:読出応答,73:通知
        format_echonet_lite[5]: opc, #OPC 取得コマンド数
        format_echonet_lite[6]: epc, #EPC コマンド
        format_echonet_lite[7]: pdc, #PDC 制御コマンド数
        format_echonet_lite[8]: edt #EDT レスポンス
    }
    frame = ''
    for key in format_echonet_lite:
        frame += data_format[key]
    return frame

def getnow():
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    return f'{now:%Y%m%d%H%M}'

def tohexymd(now):
    yyyy, mm, dd = now[:4], now[4:6], now[6:8]
    return f'{int(yyyy):04x}{int(mm):02x}{int(dd):02x}'

def getnowhexymd():
    return tohexymd(getnow())

def getnowhexhm():
    now = getnow()
    hh, mm = now[8:10], now[10:]
    return f'{int(hh):02x}{int(mm):02x}'

def diffymd(tstr):
    dt1 = datetime.strptime(tstr, '%Y%m%d')
    dt2 = datetime.strptime(getnow()[:8], '%Y%m%d')
    dif = abs(dt2 - dt1)
    return dif.days

if __name__ == '__main__':
    try:
        sf = SFComWeb.SFComWeb(SFCfg.SFMON_ADDR, SFCfg.USERID, SFCfg.PASSWD)
        print(sf.getpvw())
        print(sf.getpvval(sf.getsfweb(), 0))
        receive_multi(sf)
    except Exception as e:
        msg = str(list(traceback.TracebackException.from_exception(e).format()))
        print(msg.replace('\\n', '\n'), flush=True)

