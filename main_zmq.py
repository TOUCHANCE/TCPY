import time
from tcoreapi_mq import * 
import tcoreapi_mq
import threading

g_TradeZMQ = None
g_QuoteZMQ = None
g_TradeSession = ""
g_QuoteSession = ""
ReportID=""

#實時行情回補
def OnRealTimeQuote(symbol):
    print("實時行情",symbol["HighPrice"])

#實時Greeks回補
def OnGreeks(greek):
    print("實時Greeks",greek)

#已登入資金帳號變更
def OnGetAccount(account):
    print(account["BrokerID"])

#實時委託回報消息
def OnexeReport(report):
    global ReportID
    print("OnexeReport:", report["ReportID"])
    ReportID=report["ReportID"]
    return None

#實時成交回報回補
def RtnFillReport(report):
    print("RtnFillReport:", report["ReportID"])

#查詢當日歷史委託回報回補
def ShowEXECUTIONREPORT(ZMQ,SessionKey,reportData):
    if reportData["Reply"] == "RESTOREREPORT":
        Orders = reportData["Orders"]
        if len(Orders) == 0:
            return
        last = ""
        for data in Orders:
            last = data
            print("查詢回報",data)
        reportData = g_TradeZMQ.QryReport(SessionKey,last["QryIndex"])
        ShowEXECUTIONREPORT(g_TradeZMQ,SessionKey,reportData)

#查詢當日歷史委託成交回補
def ShowFillReport(ZMQ,SessionKey,reportData):
    if reportData["Reply"] == "RESTOREFILLREPORT":
        Orders = reportData["Orders"]
        if len(Orders) == 0:
            return

        last = ""
        for data in Orders:
            last = data
            print("查詢成交回報",data)
        reportData = g_TradeZMQ.QryFillReport(SessionKey,last["QryIndex"])
        ShowFillReport(g_TradeZMQ,SessionKey,reportData)
#查詢部位消息回補
def ShowPOSITIONS(ZMQ,SessionKey,AccountMask,positionData):
    if positionData["Reply"] == "POSITIONS":
        position = positionData["Positions"]
        if len(position) == 0:
            return

        last = ""
        for data in position:
            last = data
            print("部位:" + data["Symbol"])

        positionData = g_TradeZMQ.QryPosition(SessionKey,AccountMask,last["QryIndex"])
        ShowPOSITIONS(g_TradeZMQ,SessionKey,AccountMask,positionData)


#交易消息接收
def trade_sub_th(obj,sub_port,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=5000           #ZMQ超時設定
    socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while True:
        message =  socket_sub.recv()
        if message:
            message = json.loads(message[:-1])
            #print("in trade message",message)
            if(message["DataType"] == "ACCOUNTS"):
                for i in message["Accounts"]:
                    OnGetAccount(i)
            elif(message["DataType"] == "EXECUTIONREPORT"):
                OnexeReport(message["Report"])
            elif(message["DataType"] == "FILLEDREPORT"):
                RtnFillReport(message["Report"])

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

    global g_TradeZMQ
    global g_QuoteZMQ
    global g_TradeSession
    global g_QuoteSession

    #登入
    g_TradeZMQ = TradeAPI("ZMQ","8076c9867a372d2a9a814ae710c256e2")
    g_QuoteZMQ = QuoteAPI("ZMQ","8076c9867a372d2a9a814ae710c256e2")
    
    t_data = g_TradeZMQ.Connect("51207")
    q_data = g_QuoteZMQ.Connect("51237")
    print(t_data)
    print(q_data)

    if q_data["Success"] != "OK":
        print("[quote]connection failed")
        return

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return

    g_TradeSession = t_data["SessionKey"]
    g_QuoteSession = q_data["SessionKey"]

    #登出
    #q_logout= g_QuoteZMQ.Logout(q_data["SessionKey"])
    #print(q_logout)
    #t_logout= g_TradeZMQ.Logout(t_data["SessionKey"])
    #print(t_logout)

    #查詢指定合约訊息
    print("查詢指定合約：",g_QuoteZMQ.QueryInstrumentInfo(g_QuoteSession,"TC.F.TWF.FITX.HOT"))
    #查詢指定類型合約列表
    #期貨：Future
    #期權：Options
    #證券：Stock
    print("查詢合約：",g_QuoteZMQ.QueryAllInstrumentInfo(g_QuoteSession,"Stock"))

#####################################################################行情################################################
    #建立一個行情線程
    t2 = threading.Thread(target = quote_sub_th,args=(g_QuoteZMQ,q_data["SubPort"],))
    t2.start()
    #實時行情訂閱
    #解除訂閱
    g_QuoteZMQ.UnsubQuote(g_QuoteSession,"TC.F.TWF.FITX.HOT")
    #訂閱實時行情
    g_QuoteZMQ.SubQuote(g_QuoteSession,"TC.F.TWF.FITX.HOT")

    #實時Greeks訂閱
    #解除訂閱
    g_QuoteZMQ.UnsubGreeks(g_QuoteSession,"TC.F.TWF.FITX.HOT")
    #訂閱實時行情
    g_QuoteZMQ.SubGreeks(g_QuoteSession,"TC.F.TWF.FITX.HOT")

    #訂閱歷史數據
    g_QuoteZMQ.SubHistory(g_QuoteSession, "TC.F.TWF.FITX.HOT", "1K", "2020113000", "2020120100")


#######################################################################交易##################################################
    #建立一個交易線程
    t1 = threading.Thread(target = trade_sub_th,args=(g_TradeZMQ,t_data["SubPort"],))
    t1.start()
    #查詢已登入資金帳號
    accountInfo = g_TradeZMQ.QryAccount(g_TradeSession)
    strAccountMask=""
    if accountInfo != None:
        arrInfo = accountInfo["Accounts"]
        if len(arrInfo) != 0:
            #print("@@@@@@@@@@@:",arrInfo[0],"\n")
            strAccountMask = arrInfo[0]["AccountMask"]
            
            #查詢委託紀錄
            reportData = g_TradeZMQ.QryReport(g_TradeSession,"")
            ShowEXECUTIONREPORT(g_TradeZMQ,g_TradeSession,reportData)
            fillReportData = g_TradeZMQ.QryFillReport(g_TradeSession,"")
            ShowFillReport(g_TradeZMQ,g_TradeSession,fillReportData)

            #查詢資金
            if strAccountMask !="":
                print(g_TradeZMQ.QryMargin(g_TradeSession,strAccountMask))
            
            #查詢持倉
            positionData = g_TradeZMQ.QryPosition(g_TradeSession,strAccountMask,"")
            ShowPOSITIONS(g_TradeZMQ,g_TradeSession,strAccountMask,positionData)

            #下單
            orders_obj = {
            "Symbol":"TC.F.TWF.FITX.HOT",
            "BrokerID":arrInfo[0]['BrokerID'],
            "Account":arrInfo[0]['Account'],
            "Price":"0.0015",
            "TimeInForce":"1",
            "Side":"1",
            "OrderType":"2",
            "OrderQty":"1",
            "PositionEffect":"0"
            }
            s_order = g_TradeZMQ.NewOrder(g_TradeSession,orders_obj)

            if s_order['Success']=="OK":
                print("下單成功")
            elif s_order['ErrCode']=="-10":
                print("unknow error")
            elif s_order['ErrCode']=="-11":
                print("買賣別錯誤")
            elif s_order['ErrCode']=="-12":
                print("複式單商品代碼解析錯誤 ")
            elif s_order['ErrCode']=="-13":
                print("下單帳號,不可下此交易所商品")
            elif s_order['ErrCode']=="-14":
                print("下單錯誤,不支持的 價格 或 OrderType 或 TimeInForce")
            elif s_order['ErrCode']=="-15":
                print("不支援證券下單")
            elif s_order['ErrCode']=="-20":
                print("未建立連線")
            elif s_order['ErrCode']=="-22":
                print("價格的 TickSize 錯誤")
            elif s_order['ErrCode']=="-23":
                print("下單數量超過該商品的上下限 ")
            elif s_order['ErrCode']=="-24":
                print("下單數量錯誤 ")
            elif s_order['ErrCode']=="-25":
                print("價格不能小於和等於 0 (市價類型不會去檢查) ")

            #改單
            reporders_obj={
                "ReportID":"142733892F",
                "ReplaceExecType":"0",
                "Price":"0.021"
                }
            reorder=g_TradeZMQ.ReplaceOrder(g_TradeSession,reporders_obj)

            #刪單
            print("%%%%%%%%%%%%%%%%%%%%%%%%%",reorder)
            canorders_obj={
                "ReportID":"142921137H",
                }
            canorder=g_TradeZMQ.CancelOrder(g_TradeSession,canorders_obj)
            print("%%%%%%%%%%%%%%%%%%%%%%%%%",canorder)

if __name__ == '__main__':
    main()