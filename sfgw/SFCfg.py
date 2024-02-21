#フロンティアモニターログイン情報
USERID = 'ログインＩＤ'
PASSWD = 'パスワード'

#フロンティアホームサーバのIPアドレス
SFMON_ADDR = '192.168.0.xxx'

#マルチキャストアドレス・ポート
MULTI_ADDR = '224.0.23.0'
#自IPアドレス
LOCAL_ADDR = '0.0.0.0'

#EchonetLightポート番号
ECHONET_PORT = 3610

#容量(W)
PVW_SPEC = 3400
#設置年月日(yyyymmdd)
PVSET_YMD = '20140401'

# メーカーコード[3byte]
PV_MAKER = '000064'
# 商品コード[MAX12byte]
PV_PRDCT = '4547532d4c4d313030300000'
# 製造番号[MAX13byte]
PV_LOTNO = '30303030303030000000000000'
# 識別番号（FE＋メーカーコード[3byte]＋製造番号[13byte]）[計17byte]
PV_NODEN = 'fe' + PV_MAKER + PV_LOTNO

