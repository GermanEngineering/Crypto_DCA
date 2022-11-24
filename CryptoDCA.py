import logging
import time
from datetime import datetime, timedelta
import os
import ApiKraken
import HelperFunctions
import Database
import EMail
import math
import threading
import sys


def PlaceOrder(pair, orderType, volume, ask, latestOrder, exchangeApi):
    timeInvestStart = datetime.strptime(latestOrder[1], '%Y-%m-%d %H:%M:%S.%f')
    dbInfo = [tableName, latestOrder[0], latestOrder[0], timeInvestStart, datetime.now(), pair.get("name"), orderType, ask, ask * volume, volume, 0, "open"]

    exchangeApi.OpenOrder(pair.get("name"), orderType, volume, ask, dbInfo)


def CloseOrder(ordertxid, exchangeApi):
    response = exchangeApi.CloseOrder(ordertxid)

    if len(response.get("error")) != 0:
        logger.error(response)


def CheckIfNewOrderShouldBePlaced(pair, timeInvestStart, latestOrder, exchangeApi):
    timeSinceLastOrder = time.time() - datetime.timestamp(timeInvestStart)

    ask = exchangeApi.GetCurrentPrice(pair.get("name"))
    if ask == None:
        return
    if settings.find("HalfPriceForDebugging").text.lower() == "true":
        ask /= 2

    volume = timeSinceLastOrder * pair.get("investPerMonth") / 30 / 24 / 60 / 60 / ask
    volumeMin = pair.get("minimumOrder")

    if volume >= volumeMin:
        volume = math.floor(volume / volumeMin) * volumeMin
        ask = math.ceil(10**pair.get("digitsPrice") * ask) / 10**pair.get("digitsPrice")

        PlaceOrder(pair, orderType, volume, ask, latestOrder, exchangeApi)
        time.sleep(2)


def Initialize(settings):
    # check if keys are present
    fileName = "kraken.keys"
    if not os.path.exists(fileName):
        HelperFunctions.CreateApiKeys(fileName)    
    
    # get exchange API object
    exchangeApi = ApiKraken.ApiKraken(logger, settings, databaseTrades)

    # send info start mail
    # EMail.SendEmail("From@ab.com", "To@ab.com", f"CryptoDCA started =) {os.getcwd()}", f"LetsGooo...\n{os.getcwd()}\n{sys.argv[0]}")

    return exchangeApi


def PrepareNewLoop(settings, exchangeApi):
    logger.setLevel(logging.getLevelName(settings.find("LoggingLevel").text))

    executionInterval = 3597
    executionInterval = int(settings.find(f"ExecutionInterval").text)

    pairs = []
    for pair in settings.find("Pairs"):
        pairDict = {}
        pairDict["name"] = pair.tag
        pairDict["investPerMonth"] = float(settings.find(f"Pairs/{pair.tag}/InvestPerMonth").text)
        pairDict["exchange"] = settings.find(f"Pairs/{pair.tag}/Exchange").text.lower()
        pairDict["minimumOrder"] = None
        pairDict["digitsVolume"] = None
        pairDict["digitsPrice"] = None
        pairDict["fees"] = None
        pairs.append(pairDict)

    pairs = exchangeApi.GetPairsInfo(pairs)

    return executionInterval, pairs


if __name__ == '__main__':
    try:
        logger = HelperFunctions.GetLogger(os.path.basename(__file__))
        settings = HelperFunctions.GetSettings()
        logger.setLevel(logging.getLevelName(settings.find("LoggingLevel").text))
        logger.info(f"-- CryptoDCA.py started -- {os.getcwd()} - {sys.argv[0]}")     
        
        tableName = settings.find("Databases/Orders").tag
        tableColumns = settings.find("Databases/Orders/Columns").text
        databaseTrades = Database.Database(logger, settings.find("Databases/Orders/FileName").text, [tableName], settings.find("Databases/Orders/CreateColumns").text) 
        orderType = "buy"
        waitInterval = 21
        exchangeApi = Initialize(settings)
        pairsPreviousLoop = []

        while True:
            try:
                logger.debug("- new loop -")            
                whileLoopStartTime = time.time()
                settings = HelperFunctions.GetSettings()

                if settings.find("StartOrStop").text.lower() == "stop":
                    time.sleep(int(settings.find(f"ExecutionInterval").text))
                    continue

                executionInterval, pairs = PrepareNewLoop(settings, exchangeApi)

                # delete pairs from db that are deleted from settings.xml
                if pairsPreviousLoop != []:
                    for pair in pairsPreviousLoop:
                        if pair not in pairs:
                            latestOrder = databaseTrades.GetLatestOrder(tableName, pair.get('pair'))
                            ordertxid = latestOrder[0][0]
                            databaseTrades.DeleteOrder(tableName, ordertxid)
                pairsPreviousLoop = pairs

                for pair in pairs:
                    time.sleep(2)
                    pairName = pair.get('name')

                    # get last open or closed order from db
                    latestOrder = databaseTrades.GetLatestOrder(tableName, pairName)

                    if len(latestOrder) == 0:
                        # Case 1 (empty database)
                        timeInvestStart = datetime.now()
                        timeOrder = datetime.now()
                        databaseTrades.AddNewOrder(tableName, tableColumns, (f"{pairName}_{timeInvestStart.strftime('%Y%m%d_%H%M%S')}", timeInvestStart, timeOrder, pairName, orderType, 0, 0, 0, 0, "notPlaced"))

                    else:
                        latestOrder = latestOrder[0]
                        # check db order state
                        ordertxid = latestOrder[0]
                        timeInvestStart = datetime.strptime(latestOrder[1], '%Y-%m-%d %H:%M:%S.%f')
                        price = latestOrder[5]
                        cost = latestOrder[6]
                        volume = latestOrder[7]
                        orderStateDb =  latestOrder[9]
                        
                        if orderStateDb == "open":
                            # check order state at kraken
                            response = exchangeApi.GetOrderInfo(ordertxid)
                            # time.sleep(10)   # wait for db update message in case of websocket api usage

                            orderStateExchange = response.get("result").get(ordertxid).get("status")
                            if orderStateExchange == "closed":
                                # Case 2 (order was placed during last loop and executed)
                                timeInvestStart = datetime.fromtimestamp(response.get("result").get(ordertxid).get("closetm"))
                                feeFromOrder = float(response.get("result").get(ordertxid).get("fee"))
                                feeFromPercent = math.ceil(10**4 * pair.get("fees") / 100 * cost) / 10**4
                                fee = max(feeFromOrder, feeFromPercent)
                                databaseTrades.UpdateOrder(tableName, ordertxid, fee, "closed", timeInvestStart)
                                logger.info(f"Order executed: pair: {pairName} ordertxid: {ordertxid} price: {price} volume: {volume} cost: {cost}")
                                
                                timeInvestStart = timeInvestStart + timedelta(seconds=1)
                                databaseTrades.AddNewOrder(tableName, tableColumns, (f"{pairName}_{timeInvestStart.strftime('%Y%m%d_%H%M%S')}", timeInvestStart, timeInvestStart, pairName, orderType, 0, 0, 0, 0, "notPlaced"))
                                CheckIfNewOrderShouldBePlaced(pair, timeInvestStart, latestOrder, exchangeApi)

                            elif orderStateExchange == "open":
                                # Case 3 (order was placed during last loop but not executed)
                                timeOrder = datetime.now()
                                CloseOrder(ordertxid, exchangeApi)
                                databaseTrades.UpdateOrder(tableName, ordertxid, 0, "notPlaced", timeOrder)
                                CheckIfNewOrderShouldBePlaced(pair, timeInvestStart, latestOrder, exchangeApi)
                                
                        elif orderStateDb == "notPlaced":
                            # Case 4 (no order placed)
                            CheckIfNewOrderShouldBePlaced(pair, timeInvestStart, latestOrder, exchangeApi)

                        elif orderStateDb == "closed":
                            # Case 5 (last order was closed)
                            timeInvestStart = datetime.now()
                            timeOrder = datetime.now()
                            databaseTrades.AddNewOrder(tableName, tableColumns, (f"{pairName}_{timeInvestStart.strftime('%Y%m%d_%H%M%S')}", timeInvestStart, timeOrder, pair, orderType, 0, 0, 0, 0, "notPlaced"))

                        else:
                            # Case 6 (should not happen)
                            timeInvestStart = datetime.now()
                            timeOrder = datetime.now()
                            logger.warning(f"Could not find state of last order - ordertxid: {ordertxid}, state: {orderStateDb}")

                # sleep until next execution
                sleepTime = max(executionInterval - (time.time() - whileLoopStartTime), 0.001)
                time.sleep(sleepTime)
                waitInterval = max(waitInterval / 2, 21)
                
            except Exception as ex:
                logger.exception(ex)
                print(f"EXCEPTION: {ex}")

                # EMail.SendEmail("PythonSmtplibMail@gmail.com", "pkrueckel@gmail.com", "CryptoDCA Error", f"EXCEPTION: {ex}")
                # threadSendEMail = threading.Thread(target=EMail.SendEmail, args=("From@ab.com", "To@ab.com", "CryptoDCA Error", f"{os.getcwd()}\n{sys.argv[0]}\n{ex}"), daemon=True)
                # threadSendEMail.start()
                
                logger.warning(f"Trying to restart in {waitInterval} s.")
                time.sleep(waitInterval)
                waitInterval = min(waitInterval * 2, executionInterval)
            
    except Exception as ex:
        logger.exception(ex)
        print(f"EXCEPTION: {ex}")

    finally:
        databaseTrades.CloseConnection()
        logger.error(f"CryptoDCA stoped.")
        # EMail.SendEmail("From@ab.com", "To@ab.com", "CryptoDCA Stopped", f"Warning, CryptoDCA stoped.\n{os.getcwd()}\n{sys.argv[0]}")
