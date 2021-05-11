import time
from tcoreapi_mq import *
import tcoreapi_mq
import threading

g_QuoteZMQ = None
g_QuoteSession = ""
BuyerParam = {
    "Money":"2000000",
    "HoldValue":"0",
    "ShortAverage":"0",
    "LongAverage":"0",
    "Side":"0",
    "TradeTimes":0
}

ShoAvg = [0,0,0,0,0]
LonAvg = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

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

def AverageHandler(Price):
    global ShoAvg,LonAvg,BuyerParam
    for i in range(4):
        ShoAvg[i] = ShoAvg[i+1]
    ShoAvg[4] = Price
    if (ShoAvg[0] != 0):
        intAvg = 0
        for i in range(5):
            intAvg = intAvg + ShoAvg[i]
        intAvg = int(round(float(intAvg)/5))
        BuyerParam['ShortAverage'] = str(intAvg)
    for i in range(19):
        LonAvg[i] = LonAvg[i+1]
    LonAvg[19] = Price
    if (LonAvg[0] != 0):
        intAvg = 0
        for i in range(20):
            intAvg = intAvg +LonAvg[i]
        intAvg = int(round(float(intAvg)/20))
        BuyerParam['LongAverage'] = str(intAvg)

def TradeHadler(Price,Kbar):
    global BuyerParam
    floatMoney = float(BuyerParam['Money'])
    intHoldValue = int(BuyerParam['HoldValue'])
    intShoAvg = int(BuyerParam['ShortAverage'])
    intLonAvg = int(BuyerParam['LongAverage'])
    intSide = int(BuyerParam['Side'])
    ValChange = floatMoney - (intHoldValue - Price)*200
    if (intHoldValue == 0):
        ValChange = floatMoney
    if (intSide == 0 and intShoAvg > intLonAvg and intLonAvg != 0):
        floatMoney = str(ValChange)
        BuyerParam['HoldValue'] = str(Price)
        BuyerParam['Side'] = '1'
        BuyerParam['TradeTimes'] = BuyerParam['TradeTimes'] + 1
        Move = "第"+str(Kbar)+"根K棒，短線："+BuyerParam['ShortAverage']+"，長線："+BuyerParam['LongAverage']+"，買進一口，進場點位："+str(Price)+\
               "，第"+str(BuyerParam['TradeTimes'])+"次進場\n當前權益數："+floatMoney
        KeepNote(Move)
    elif(intSide == 1 and ValChange <= floatMoney*0.95):
        BuyerParam['Money'] = str(ValChange)
        BuyerParam['HoldValue'] = '0'
        BuyerParam['Side'] = '0'
        Move = "第"+str(Kbar)+"根K棒，短線："+BuyerParam['ShortAverage']+"，長線："+BuyerParam['LongAverage']+"，停損出場，進場點位：" + str(Price) + \
               "，第"+str(BuyerParam['TradeTimes'])+"次出場\n當前權益數：" + BuyerParam['Money']
        KeepNote(Move)
    elif(intSide == 1 and intShoAvg <= intLonAvg):
        BuyerParam['Money'] = str(ValChange)
        BuyerParam['HoldValue'] = '0'
        GP = Price - intHoldValue
        BuyerParam['Side'] = '0'
        Move = "第"+str(Kbar)+"根K棒，短線："+BuyerParam['ShortAverage']+"，長線："+BuyerParam['LongAverage']+"，策略出場，出場點位："+str(Price)+\
               "，第"+str(BuyerParam['TradeTimes'])+"次出場\n損益"+str(GP)+"點，相當於"+str(GP*200)+"元，當前權益數："+BuyerParam['Money']
        KeepNote(Move)

def KeepNote(Note):
    f = open("績效紀錄.txt", 'a')
    f.write(Note+"\n")
    f.close()

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
    type = "1K"
    #起始時間
    StrTim = '2020030100'
    #結束時間
    EndTim = '2021042200'
    #資料頁數
    QryInd = '0'

    #訂閱歷史資料
    SubHis = g_QuoteZMQ.SubHistory(g_QuoteSession,quoteSymbol,type,StrTim,EndTim)
    print("訂閱歷史資料:",SubHis)
    while(1):  #等待訂閱回補
        HisData = g_QuoteZMQ.GetHistory(g_QuoteSession, quoteSymbol, type, StrTim, EndTim, QryInd)
        if (len(HisData['HisData']) != 0):
            print("回補成功")
            break
        time.sleep(1)

    #開始使用獲取的歷史資料進行回測
    level = 0
    while (1):
        global BuyerParam
        HisData = g_QuoteZMQ.GetHistory(g_QuoteSession, quoteSymbol, type, StrTim, EndTim, QryInd)
        for i in range(50):
            Kbar = level+i+1
            OrdPrice = int(HisData['HisData'][i]['Close'])
            AverageHandler(OrdPrice)
            print("第" + str(Kbar) +"根K棒，收盤價：", OrdPrice)
            print("短線："+BuyerParam['ShortAverage']+",長線："+BuyerParam['LongAverage'])
            TradeHadler(OrdPrice,Kbar)
        QryInd = str(int(QryInd) + 50)
        level = level + 50

if __name__ == '__main__':
    main()
