import krakenex
import requests
import HelperFunctions


class ApiKraken(object):

    def __init__(self, logger, settings, databaseTrades):
        self.logger = logger
        self.settings = settings        
        self.databaseTrades = databaseTrades
        self.tickerURL = "https://api.kraken.com/0/public/Trades?pair=%s"
        self.depthURL = "https://api.kraken.com/0/public/Depth?pair=%s"

        self.krakenApi = krakenex.API()
        self.krakenApi.key, self.krakenApi.secret = HelperFunctions.Decrypt("kraken.keys")


    """def GetBalance(self):
        response = self.krakenApi.query_private("Balance")
        balance = float(response.get("result").get("ZEUR"))
        return balance

        # check for sufficient balance
        balance = self.GetBalance()
        if balance > volume * price:
            # order
            pass
        else:
            self.logger.error(f"Insufficient funds! Balance: {balance} EUR / Order: {volume} {pair} = {volume * price} EUR") """


    def GetOrderInfo(self, txid):
        response = self.krakenApi.query_private("QueryOrders", data = {"txid":txid})
        return response


    def OpenOrder(self, pair, orderType, volume, price, dbInfo):
        # https://www.kraken.com/features/api#add-standard-order
        self.logger.info(f"Try to open order: {pair, orderType, volume, price}")

        # open order
        response = self.krakenApi.query_private("AddOrder", data = {"pair":pair, "type":orderType, "ordertype":"limit", "volume":volume, "price":price})        
        self.logger.debug(f"OpenOrder: {response}")

        if len(response.get("result")) != 0:
            if self.settings.find("HalfPriceForDebugging").text.lower() != "true":
                dbInfo[2] = response.get("result").get("txid")[0]
            
            self.databaseTrades.UpdateOrderPlaced(dbInfo[0], dbInfo[1], dbInfo[2], dbInfo[3], dbInfo[4], dbInfo[5], dbInfo[6], dbInfo[7], dbInfo[8], dbInfo[9], dbInfo[10], dbInfo[11])
        else:
            self.logger.error(response)
            

    def CloseOrder(self, txid):
        response = self.krakenApi.query_private("CancelOrder", {"txid":txid})

        self.logger.info(f"CloseOrder {txid} Response: {response}")
        return response


    def GetCurrentPrice(self, pair):
        response = self.krakenApi.query_public("Ticker", data = {"pair": pair})

        """ # https://docs.kraken.com/websockets/ ticker
        #response = requests.get("https://api.kraken.com/0/public/Ticker?pair=XDGEUR")
        url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
        response = self.ApiRequest(url) """

        for prices in response.get("result").values():
            price = float(prices.get("c")[0])
            ask = float(prices.get("a")[0])
            bid = float(prices.get("b")[0])
            break
        
        #self.logger.debug(f"GetCurrentPrice: {pair, price, ask, bid}")
        return ask


    def GetPairsInfo(self, pairs):
        response = requests.get("https://api.kraken.com/0/public/AssetPairs")
        responseDict = response.json()
        assetPairs = responseDict.get("result")

        for pair in pairs:
            name = pair.get("name")
            values = assetPairs.get(name)
            if values != None:
                pair["minimumOrder"] = float(values.get("ordermin"))
                pair["digitsVolume"] = int(values.get("lot_decimals"))
                pair["digitsPrice"] = int(values.get("pair_decimals"))
                pair["fees"] = float(values.get("fees")[0][1])
            else:
                self.logger.warning(f"Could not find data for: {name}")            

        return pairs
