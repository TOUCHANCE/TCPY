import time
from tcoreapi_mq import * 
import tcoreapi_mq
import threading

g_QuoteZMQ = None
g_QuoteSession = ""

#實時行情回補
def OnRealTimeQuote(symbol):
    print("商品：", symbol["Symbol"], "成交價:",symbol["TradingPrice"], "開:", symbol["OpeningPrice"], "高:", symbol["HighPrice"], "低:", symbol["LowPrice"])

#行情消息接收
def quote_sub_th(obj,sub_port,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=7000   #ZMQ超時設定
    socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while(True):
        message = (socket_sub.recv()[:-1]).decode("utf-8")
        index =  re.search(":",message).span()[1]  # filter
        message = message[index:]
        message = json.loads(message)
        #for message in messages:
        if(message["DataType"]=="REALTIME"):
            OnRealTimeQuote(message["Quote"])
        elif(message["DataType"]=="GREEKS"):
            OnGreeks(message["Quote"])
        elif(message["DataType"]=="TICKS" or message["DataType"]=="1K" or message["DataType"]=="DK" ):
            #print("@@@@@@@@@@@@@@@@@@@@@@@",message)
            strQryIndex = ""
            while(True):
                s_history = obj.GetHistory(g_QuoteSession, message["Symbol"], message["DataType"], message["StartTime"], message["EndTime"], strQryIndex)
                historyData = s_history["HisData"]
                if len(historyData) == 0:
                    break

                last = ""
                for data in historyData:
                    last = data
                    #print("歷史行情：Time:%s, Volume:%s, QryIndex:%s" % (data["Time"], data["Volume"], data["QryIndex"]))
                
                strQryIndex = last["QryIndex"]
                    
    return


def main():

    global g_QuoteZMQ
    global g_QuoteSession

    #登入(與 TOUCHANCE zmq 連線用，不可改)
    g_QuoteZMQ = QuoteAPI("ZMQ","8076c9867a372d2a9a814ae710c256e2")
    q_data = g_QuoteZMQ.Connect("51237")
    print("q_data=",q_data)

    if q_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    g_QuoteSession = q_data["SessionKey"]


    #查詢指定合约訊息
    quoteSymbol = "TC.F.TWF.FITX.HOT"
    #print("查詢指定合約：",g_QuoteZMQ.QueryInstrumentInfo(g_QuoteSession, quoteSymbol))
    #查詢指定類型合約列表
    #期貨：Fut
    #期權：Opt
    #證券：Sto
    #print("查詢合約：",g_QuoteZMQ.QueryAllInstrumentInfo(g_QuoteSession,"Fut"))

#####################################################################行情################################################
    #建立一個行情線程
    t2 = threading.Thread(target = quote_sub_th,args=(g_QuoteZMQ,q_data["SubPort"],))
    t2.start()

    #資料週期
    type = "TICKS"
    #起始時間
    StrTim = '2021032100'
    #結束時間
    EndTim = '2021032300'
    #資料頁數
    QryInd = '0'

    #訂閱歷史資料
    SubHis = g_QuoteZMQ.SubHistory(g_QuoteSession,quoteSymbol,type,StrTim,EndTim)
    print("訂閱歷史資料:",SubHis)
    #等待回補
    #獲取回補的資料
    i = 0
    x = 1
    while(1):  #等待訂閱回補
        QPong = g_QuoteZMQ.Pong(g_QuoteSession)
        print("第"+str(i*x)+"秒，Pong:",QPong)
        HisData = g_QuoteZMQ.GetHistory(g_QuoteSession, quoteSymbol, type, StrTim, EndTim, QryInd)
        if (len(HisData['HisData']) != 0):
            print("回補成功")
            i = 0
            break
        print("取得歷史資料:", HisData)
        i = i + 1
        time.sleep(x)
    f = open("歷史資料(TICKS).txt", 'w')
    f.close()
    while (1):  # 獲取訂閱成功的全部歷史資料並另存
        QPong = g_QuoteZMQ.Pong(g_QuoteSession)
        print(QPong)
        HisData = g_QuoteZMQ.GetHistory(g_QuoteSession, quoteSymbol, type, StrTim, EndTim, QryInd)
        for j in range(50):
            print("第"+str(j+QryInd)+"筆：")
            print(HisData['HisData'][j])
            f = open("歷史資料(TICKS).txt", 'a')
            for key in HisData['HisData'][j]:
                f.write(key + "：" + HisData['HisData'][j][key] + ",")
            f.write('\n')
            i = j
        QryInd = str(int(QryInd) + i)

if __name__ == '__main__':
    main()
