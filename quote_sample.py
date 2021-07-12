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
                    print("歷史行情：Time:%s, Volume:%s, QryIndex:%s" % (data["Time"], data["Volume"], data["QryIndex"]))
                
                strQryIndex = last["QryIndex"]
                    
    return


def main():

    global g_QuoteZMQ
    global g_QuoteSession

    #登入(與 TOUCHANCE zmq 連線用，不可改)
    g_QuoteZMQ = QuoteAPI("ZMQ","8076c9867a372d2a9a814ae710c256e2")
    q_data = g_QuoteZMQ.Connect("51237")
    print(q_data)

    if q_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    g_QuoteSession = q_data["SessionKey"]


    #查詢指定合约訊息
    quoteSymbol = "TC.F.TWF.FIMTX.HOT"
    #print("查詢指定合約：",g_QuoteZMQ.QueryInstrumentInfo(g_QuoteSession, quoteSymbol))
    #查詢指定類型合約列表
    #期貨：FUT
    #期權：OPT
    #證券：STF
    #print("查詢合約：",g_QuoteZMQ.QueryAllInstrumentInfo(g_QuoteSession,"FUT"))

#####################################################################行情################################################
    #建立一個行情線程
    t2 = threading.Thread(target = quote_sub_th,args=(g_QuoteZMQ,q_data["SubPort"],))
    t2.start()
    #實時行情訂閱
    #解除訂閱
    g_QuoteZMQ.UnsubQuote(g_QuoteSession, quoteSymbol)
    #訂閱實時行情
    g_QuoteZMQ.SubQuote(g_QuoteSession, quoteSymbol)

if __name__ == '__main__':
    main()
