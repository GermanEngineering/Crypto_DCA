import sqlite3

class Database(object):    
    def __init__(self, logger, databaseFile, tableNames=[], columns=[]):
        self.logger = logger
        self.__connection = sqlite3.connect(databaseFile)
        self.__cursor = self.__connection.cursor()
        self.dbUpdated = False

        for tableName in tableNames:
            self.__cursor.execute(f"CREATE TABLE IF NOT EXISTS {tableName} ({columns})")


    def GetLatestOrder(self, tableName, pair):
        self.__cursor.execute(f"SELECT * FROM {tableName} WHERE Pair='{pair}' ORDER BY timeOrder DESC LIMIT 1")
        return self.__cursor.fetchall()


    def AddNewOrder(self, tableName, columnNames, data):
        self.logger.debug(f"INSERT OR IGNORE INTO {tableName} ({columnNames}) VALUES ({','.join(len(columnNames.split(',')) * '?')}) , Data: {data}")
        self.__cursor.execute(f"INSERT OR IGNORE INTO {tableName} ({columnNames}) VALUES ({','.join(len(columnNames.split(',')) * '?')})", data)
        self.__connection.commit()
        self.dbUpdated = True


    def UpdateOrder(self, tableName, ordertxid, fee, orderState, timeOrder):
        self.logger.debug(f"UPDATE {tableName} SET fee='{fee}', orderState='{orderState}', timeOrder='{timeOrder}' WHERE orderTxId='{ordertxid}'")
        self.__cursor.execute(f"UPDATE {tableName} SET fee='{fee}', orderState='{orderState}', timeOrder='{timeOrder}' WHERE orderTxId='{ordertxid}'")
        self.__connection.commit()
        self.dbUpdated = True


    def UpdateOrderPlaced(self, tableName, oldOrderTxId, orderTxId, timeInvestStart, timeOrder, pair, orderType, price, cost, volume, fee, orderState):
        self.logger.debug(f"UPDATE {tableName} SET orderTxId='{orderTxId}', timeInvestStart='{timeInvestStart}', timeOrder='{timeOrder}', pair='{pair}', orderType='{orderType}', price='{price}', cost='{cost}', volume='{volume}', fee='{fee}', orderState='{orderState}' WHERE orderTxId='{oldOrderTxId}'")
        self.__cursor.execute(f"UPDATE {tableName} SET orderTxId='{orderTxId}', timeInvestStart='{timeInvestStart}', timeOrder='{timeOrder}', pair='{pair}', orderType='{orderType}', price='{price}', cost='{cost}', volume='{volume}', fee='{fee}', orderState='{orderState}' WHERE orderTxId='{oldOrderTxId}'")
        self.__connection.commit()
        self.dbUpdated = True


    def DeleteOrder(self, tableName, ordertxid):
        self.logger.debug(f"DELETE FROM {tableName} WHERE orderTxId='{ordertxid}'")
        self.__cursor.execute(f"DELETE FROM {tableName} WHERE orderTxId='{ordertxid}'")
        self.__connection.commit()
        self.dbUpdated = True


    def CloseConnection(self):
        self.__connection.close()
