import logging
import config as cf
logname = cf.log_dir + "ctptensorflow.log"
filehandler = logging.FileHandler(filename=logname,mode='w',encoding="utf-8")
fmter = logging.Formatter(fmt="%(asctime)s %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
filehandler.setFormatter(fmter)
loger = logging.getLogger(__name__)
loger.addHandler(filehandler)
# ch = logging.StreamHandler()
# ch.setFormatter(fmter)
# loger.addHandler(ch)
loger.setLevel(logging.DEBUG)
loger.fatal("second log")


logname2 = cf.log_dir + "thread_monitor.log"
filehandler2 = logging.FileHandler(filename=logname2,mode='w',encoding="utf-8")
filehandler2.setFormatter(fmter)
loger2 = logging.getLogger("thread_monitor")
loger2.addHandler(filehandler2)
loger2.setLevel(logging.DEBUG)


logname3 = cf.log_dir + "order.log"
filehandler3 = logging.FileHandler(filename=logname3,mode='w',encoding="utf-8")
filehandler3.setFormatter(fmter)
loger_order = logging.getLogger("order")
loger_order.addHandler(filehandler3)
loger_order.setLevel(logging.DEBUG)

logname4 = cf.log_dir + "trader.log"
filehandler4 = logging.FileHandler(filename=logname4,mode='w',encoding="utf-8")
filehandler4.setFormatter(fmter)
loger_trader = logging.getLogger("trader")
loger_trader.addHandler(filehandler4)
loger_trader.setLevel(logging.DEBUG)

logname5 = cf.log_dir + "market_data.log"
filehandler5 = logging.FileHandler(filename=logname5,mode='w',encoding="utf-8")
filehandler5.setFormatter(fmter)
loger_market_data = logging.getLogger("market_data")
loger_market_data.addHandler(filehandler5)
loger_market_data.setLevel(logging.DEBUG)

logname6 = cf.log_dir + "account_position.log"
filehandler6 = logging.FileHandler(filename=logname6,mode='w',encoding="utf-8")
filehandler6.setFormatter(fmter)
loger_account_position = logging.getLogger("account_position")
loger_account_position.addHandler(filehandler6)
loger_account_position.setLevel(logging.DEBUG)


logname7 = cf.log_dir + "error.log"
filehandler7 = logging.FileHandler(filename=logname7,mode='w',encoding="utf-8")
filehandler7.setFormatter(fmter)
loger_error = logging.getLogger("error")
loger_error.addHandler(filehandler7)
loger_error.setLevel(logging.DEBUG)

logname8 = cf.log_dir + "cash_account.log"
filehandler8 = logging.FileHandler(filename=logname8,mode='w',encoding="utf-8")
filehandler8.setFormatter(fmter)
loger_cash_account = logging.getLogger("error")
loger_cash_account.addHandler(filehandler8)
loger_cash_account.setLevel(logging.DEBUG)


import threading

loger2.info("线程运行中。。。"+str(threading.current_thread()))
loger2.error("haha")
