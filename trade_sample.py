import time
from tcoreapi_mq import * 
import tcoreapi_mq
import threading

g_TradeZMQ = None
g_TradeSession = ""
ReportID=""

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

def main():

    global g_TradeZMQ
    global g_TradeSession

    #登入(與 TOUCHANCE zmq 連線用，不可改)
    g_TradeZMQ = TradeAPI("ZMQ","8076c9867a372d2a9a814ae710c256e2")
    t_data = g_TradeZMQ.Connect("51207")
    print(t_data)

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return

    g_TradeSession = t_data["SessionKey"]

#######################################################################交易##################################################
    #建立一個交易線程
    t1 = threading.Thread(target = trade_sub_th,args=(g_TradeZMQ,t_data["SubPort"],))
    t1.start()
    #查詢已登入資金帳號
    accountInfo = g_TradeZMQ.QryAccount(g_TradeSession)
    print("查詢已登入的資金帳號:",accountInfo)

    strAccountMask=""
    if accountInfo != None:
        arrInfo = accountInfo["Accounts"]
        if len(arrInfo) != 0:
            #print("@@@@@@@@@@@:",arrInfo[0],"\n")
            strAccountMask = arrInfo[0]["AccountMask"]
            print(strAccountMask)

            #查詢委託紀錄
            reportData = g_TradeZMQ.QryReport(g_TradeSession,"")
            print('查詢所有回報:',reportData)
            ShowEXECUTIONREPORT(g_TradeZMQ,g_TradeSession,reportData)
            fillReportData = g_TradeZMQ.QryFillReport(g_TradeSession,"")
            print('查詢成交回報:', fillReportData)
            ShowFillReport(g_TradeZMQ,g_TradeSession,fillReportData)

            #查詢資金
            if strAccountMask !="":
                print("查詢資金帳號：",g_TradeZMQ.QryMargin(g_TradeSession,strAccountMask))
            
            #查詢持倉
            positionData = g_TradeZMQ.QryPosition(g_TradeSession,strAccountMask,"")
            print('查詢持倉部位:',positionData)
            ShowPOSITIONS(g_TradeZMQ,g_TradeSession,strAccountMask,positionData)

            #下單
            orders_obj = {
            "Symbol":"TC.F.TWF.FITX.HOT",
            "BrokerID":arrInfo[0]['BrokerID'],
            "Account":arrInfo[0]['Account'],
            "Price":"15000",
            "TimeInForce":"1",
            "Side":"1",
            "OrderType":"2",
            "OrderQty":"1",
            "PositionEffect":"0"
            }
            s_order = g_TradeZMQ.NewOrder(g_TradeSession,orders_obj)
            print('下單結果:',s_order)

            """
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
            """

            #改單
            reporders_obj={
                "ReportID":"4094755221B",
                "ReplaceExecType":"0",
                "Price":"16500"
                }
            reorder=g_TradeZMQ.ReplaceOrder(g_TradeSession,reporders_obj)

            #刪單
            print("%%%%%%%%%%%%%%%%%%%%%%%%%",reorder)
            canorders_obj={
                "ReportID":"4094755221B",
                }
            canorder=g_TradeZMQ.CancelOrder(g_TradeSession,canorders_obj)
            print("%%%%%%%%%%%%%%%%%%%%%%%%%",canorder)

if __name__ == '__main__':
    main()
