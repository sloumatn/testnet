from ast import While
import binance.client 
from binance.client import Client
from binance.futures import Futures
import pandas as pd
import talib as ta
import time
import sys
import datetime
from lib2to3.pgen2.pgen import DFAState

import requests
from requests.models import to_native_string


Pkey ="6938c2fd1b24a9ed5fc59bbe563941ac759f4b8f9f4da6869103a83bb67c0a13"
Skey ="f5e41c7f8e3be7a14812a09d8f2b66838c0a2746b6dc3ddddcb72b9f474d96e5"

RR=1.6
risk=0.005

client = Client(api_key=Pkey, api_secret=Skey,testnet=True)
symbol="ETHUSDT"
timeframe="5m"
hours_ago="1 hours ago UTC"
chosen_candles= ["CDLCLOSINGMARUBOZU" ,"CDLBELTHOLD", "CDLENGULFING","CDLMARUBOZU","CDLHIKKAKE"]
intervals3= [0,5,10,15,20,25,30,35,40,45,50,55]
nl ="%0D%0A"

        
def telegram_send_message(message):
    bot_token = "5047723665:AAG66zW7HD5m0Se_mpmAbzycV7x3h4Nb7kY"
    bot_chatID = "-1001566704021"
    send_text = "https://api.telegram.org/bot"+bot_token+"/sendMessage?chat_id="+bot_chatID+"&parse_mode=Markdown&text="+message
    response = requests.get(send_text)
    return response

def fbalance() :
    fbalance=client.futures_account_balance()
    
    fbalance=float(fbalance[1]['balance'])
    return  fbalance

def getdf() :
    columns =[ "O time","O","H","L","C","V","C time","asset volume","Number of trades","Buy vol","Buy VOL VAL", "x"]
    bars = client.futures_historical_klines(symbol, timeframe, hours_ago)
    df = pd.DataFrame(bars)
    df.columns = columns
    df["O time"]=pd.to_datetime(df["O time"],unit="ms")
    df=df.set_index("O time")
    last_high=df["H"][-2]
    last_low=df["L"][-2]
    average_price=client.futures_orderbook_ticker(symbol=symbol)
    bid_price=average_price["bidPrice"]
    ask_price=average_price["askPrice"]
    df = df.drop(["V","C time","asset volume","Number of trades","Buy vol","Buy VOL VAL", "x"],axis=1)
    df["RSI"]= ta.RSI(df["C"],timeperiod=14)
    df['CDLBELTHOLD']=ta.CDLBELTHOLD(df['O'],df['H'],df['L'],df['C'])
    df['CDLCLOSINGMARUBOZU']=ta.CDLCLOSINGMARUBOZU(df['O'],df['H'],df['L'],df['C'])
    df['CDLENGULFING']=ta.CDLENGULFING(df['O'],df['H'],df['L'],df['C'])
    df['CDLMARUBOZU']=ta.CDLMARUBOZU(df['O'],df['H'],df['L'],df['C'])
    df['CDLHIKKAKE']=ta.CDLHIKKAKE(df['O'],df['H'],df['L'],df['C'])
    df['ATR'] =ta.ATR(df['H'],df['L'],df['C'],timeperiod=7)

def placeBUY(symbol , quantity , SL , TP) :
    client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)
    client.futures_create_order(symbol=symbol, side='SELL', type='STOP_MARKET',  stopPrice=SL,closePosition='true')
    client.futures_create_order(symbol=symbol, side='SELL', type='LIMIT',timeInForce='GTC',quantity=quantity , price=TP,reduceOnly='true')

def placeSELL(symbol , quantity , SL , TP) :
    client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
    client.futures_create_order(symbol=symbol, side='BUY', type='STOP_MARKET',  stopPrice=SL,closePosition='true')
    client.futures_create_order(symbol=symbol, side='BUY', type='LIMIT',timeInForce='GTC',quantity=quantity , price=TP,reduceOnly='true')

def open_orders_count() :
    open_orders = client.futures_get_open_orders()
    open_orders= len(open_orders)
    return open_orders

def open_positions_count() :
    all_position = client.futures_position_information()
    columns2 =['symbol',  'positionAmt', 'entryPrice', 'markPrice', 'unRealizedProfit', 'liquidationPrice', 'leverage', 'maxNotionalValue', 'marginType', 'isolatedMargin', 'isAutoAddMargin', 'positionSide', 'notional', 'isolatedWallet', 'updateTime']
    all_position = pd.DataFrame(all_position)
    all_position.columns = columns2
    all_positions =list(all_position['positionAmt'].astype(float))
    open_positions = 0
    for position in all_positions :
        if position >0 :
            open_positions=open_positions+1
    return open_positions

def changeleverage(symbol , leverage) :
    client.futures_change_leverage(symbol=symbol, leverage=leverage)

def servertime():
  
    status = client.get_system_status()
    stat = status["status"]
    time_server = client.get_server_time()
    if stat==0 :
        connection = "connected"
    else :
        connection = "Disconnected"
    servertime=pd.to_datetime(time_server["serverTime"],unit="ms")
    minute = int(servertime.strftime("%M"))
    second = int(servertime.strftime("%S"))
    return minute , second

def last_JC_pattern(df,ask_price ,bid_price) :
    for candle in chosen_candles : 
       if   df[candle][-2]==100 or df[candle][-2]==200 :
            SL = float(ask_price)-float(df['ATR'][-2])
            TP =float(ask_price)+float(df['ATR'][-2])*RR
            break
       elif df[candle][-2]==-100 or df[candle][-2]==-200 :
            SL = float(bid_price)+float(df['ATR'][-2])
            TP =float(bid_price) -float(df['ATR'][-2])*RR
            break

def clean_orders(openorders ,openpositions) :
    if openorders>0 and openpositions==0 :
        client.futures_cancel_orders(symbol=symbol)


while True :
    try :
        ########timeserver
        status = client.get_system_status()
        stat = status["status"]
        time_server = client.get_server_time()
        if stat==0 :
            connection = "connected"
        else :
            connection = "Disconnected"
        servertime=pd.to_datetime(time_server["serverTime"],unit="ms")
        minute = int(servertime.strftime("%M"))
        second = int(servertime.strftime("%S"))
        for i in intervals3 :
            if i==minute and (second ==5 or second==7 ) :
                ########import_data
                columns =[ "O time","O","H","L","C","V","C time","asset volume","Number of trades","Buy vol","Buy VOL VAL", "x"]
                bars = client.futures_historical_klines(symbol, timeframe, hours_ago)
                df = pd.DataFrame(bars)
                df.columns = columns
                df["O time"]=pd.to_datetime(df["O time"],unit="ms")
                df=df.set_index("O time")
                last_high=df["H"][-2]
                last_low=df["L"][-2]
                average_price=client.futures_orderbook_ticker(symbol=symbol)
                bid_price=average_price["bidPrice"]
                ask_price=average_price["askPrice"]
                df = df.drop(["V","C time","asset volume","Number of trades","Buy vol","Buy VOL VAL", "x"],axis=1)
                df["RSI"]= ta.RSI(df["C"],timeperiod=14)
                df['CDLBELTHOLD']=ta.CDLBELTHOLD(df['O'],df['H'],df['L'],df['C'])
                df['CDLCLOSINGMARUBOZU']=ta.CDLCLOSINGMARUBOZU(df['O'],df['H'],df['L'],df['C'])
                df['CDLENGULFING']=ta.CDLENGULFING(df['O'],df['H'],df['L'],df['C'])
                df['CDLMARUBOZU']=ta.CDLMARUBOZU(df['O'],df['H'],df['L'],df['C'])
                df['CDLHIKKAKE']=ta.CDLHIKKAKE(df['O'],df['H'],df['L'],df['C'])
                df['ATR'] =ta.ATR(df['H'],df['L'],df['C'],timeperiod=2)
                ##########count all positions and orders
                open_orders = client.futures_get_open_orders()
                open_orders= len(open_orders)
                all_position = client.futures_position_information()
                columns2 =['symbol',  'positionAmt', 'entryPrice', 'markPrice', 'unRealizedProfit', 'liquidationPrice', 'leverage', 'maxNotionalValue', 'marginType', 'isolatedMargin', 'isAutoAddMargin', 'positionSide', 'notional', 'isolatedWallet', 'updateTime']
                all_position = pd.DataFrame(all_position)
                all_position.columns = columns2
                all_positions =list(all_position['positionAmt'].astype(float))
                open_positions = 0
                for position in all_positions :
                    if position >0 :
                        open_positions=open_positions+1
                
                ##########import balance_and-amount_to_risk
                fbalance=client.futures_account_balance()
                fbalance=float(fbalance[1]['balance'])
                amount_to_risk =risk*fbalance
                

                ##########Clean orders
                if open_orders>0 and open_positions==0 :
                    client.futures_cancel_orders(symbol=symbol)
                
                ##########Search for candle and excute orders
                for candle in chosen_candles : 
                    if   df[candle][-2]>0 and open_positions==0:
                        SL = round(float(ask_price)-float(df['ATR'][-2]),2)
                        TP =round(float(ask_price)+float(df['ATR'][-2])*RR,2)
                        quantity = round(amount_to_risk/float(df['ATR'][-2]),3)
                        client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)
                        client.futures_create_order(symbol=symbol, side='SELL', type='STOP_MARKET',  stopPrice=SL,closePosition='true')
                        client.futures_create_order(symbol=symbol, side='SELL', type='LIMIT',timeInForce='GTC',quantity=quantity , price=TP,reduceOnly='true')
                        print()
                        print("***********")
                        print(symbol) 
                        print("bullish ",candle )
                        print("stop loss range : " , df['ATR'][-2])
                        print("stop loss price :" , SL)
                        print("take profit price : ", TP)
                        print("quantity = ",quantity)                
                        print("*************************")
                        message = [symbol,nl,"bullish ",candle,nl,"stop loss range : " ,str(df['ATR'][-2]),nl,"stop loss price :" , str(SL),nl,"take profit price : ", str(TP)]
                        messagetel="".join(message)
                        telegram_send_message(messagetel+nl+"quantity = "+str(quantity))
                        break
                    elif df[candle][-2]<0 and open_positions==0 :
                        SL = round(float(bid_price)+float(df['ATR'][-2]),2)
                        TP =round(float(bid_price) -float(df['ATR'][-2])*RR,2)
                        quantity = round(amount_to_risk/float(df['ATR'][-2]),3)
                        client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
                        client.futures_create_order(symbol=symbol, side='BUY', type='STOP_MARKET',  stopPrice=SL,closePosition='true')
                        client.futures_create_order(symbol=symbol, side='BUY', type='LIMIT',timeInForce='GTC',quantity=quantity , price=TP,reduceOnly='true')
                        
                        print("bearish ", candle)
                        print("stop loss range : " , df['ATR'][-2])
                        print("stop loss price :" , SL)
                        print("take profit price : ", TP)
                        print("quantity = ",quantity)                
                        print("*************************")
                        message = [symbol,nl,"bearish ",candle,nl,"stop loss range : " ,str(df['ATR'][-2]),nl,"stop loss price :" , str(SL),nl,"take profit price : ", str(TP)]
                        messagetel="".join(message)
                        telegram_send_message(messagetel+nl+"quantity = "+str(quantity))
                    else :
                        print("************************")
                        print(servertime)
                        print("no signal")
                        print("open positions =",open_positions) 
                        print("*********************")
                        telegram_send_message("no signal"+nl+"open positions ="+str(open_positions))
                        break
    except :
        time.sleep(15)        