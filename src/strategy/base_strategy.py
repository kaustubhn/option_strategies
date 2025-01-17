# Author : Prashant Srivastava
import logging
import time
from abc import ABC
from abc import abstractmethod


class BaseStrategy(ABC):
    def __init__(self, name: str, scrip_codes: list):
        self.scrip_codes = scrip_codes
        self.name = name
        self.logger = logging.getLogger(__name__)
        self.executed_orders = None
        self.tag = f"{self.name.lower()}{int(time.time())}"

    @abstractmethod
    def entry(self, ohlcvt: dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def exit(self, ohlcvt: dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_leg_pnl(self, code: int, avg: float, qty: int, ltp: float):
        raise NotImplementedError

    def get_pnl(self):
        # sum all the pnl of each leg
        total_pnl = None
        if self.executed_orders:
            total_pnl = 0.0
            for _, info in self.executed_orders.items():
                total_pnl += info["pnl"]
        return total_pnl

    def is_in_position(self):
        return self.executed_orders is not None

    def get_executed_order(self, code) -> (float, int):  # Avg, Qty
        if code not in self.executed_orders:
            return (None, None)
        return (self.executed_orders[code]["rate"], self.executed_orders[code]["qty"])

    def get_all_executed_orders(self):
        return self.executed_orders

    @abstractmethod
    def run(self, ohlcvt: dict, user_data: dict = None):
        # Following is done to update the ltp of the scrip in the
        # executed_orders only
        if self.is_in_position():
            ltp = ohlcvt["c"]
            code = ohlcvt["code"]
            if code in self.executed_orders:
                self.executed_orders[code]["ltp"] = ltp
                self.executed_orders[code]["pnl"] = self.get_leg_pnl(
                    code,
                    self.executed_orders[code]["rate"],
                    self.executed_orders[code]["qty"],
                    self.executed_orders[code]["ltp"],
                )

    def add_executed_orders(self, executed_orders: dict):
        if not self.executed_orders:
            self.executed_orders = {}
        self.executed_orders[executed_orders["ScripCode"]] = executed_orders

    @abstractmethod
    def order_placed(self, order: dict, _subs_list: dict, user_data: dict):
        # This will be called for "Fully Executed"" only
        # check if order["ScripCode"] is in self.scrip_codes
        # if yes, add to self.executed_orders
        self.logger.info("base strategy | order_placed: %s %s", order, self.scrip_codes)
        if order["ScripCode"] in self.scrip_codes:
            if not self.executed_orders:
                self.executed_orders = {}
            self.executed_orders[order["ScripCode"]] = {
                "rate": order["Price"],
                "qty": order["Qty"],
                "ltp": order["Price"],
                "pnl": 0.0,
            }

    @abstractmethod
    def stop(self):
        raise NotImplementedError

    @abstractmethod
    def start(self):
        raise NotImplementedError
