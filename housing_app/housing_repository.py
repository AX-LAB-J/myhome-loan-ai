"""Parameterized local DB queries. No arbitrary SQL is exposed to the LLM.

The serving database is read-only at runtime (only the geocode cache is written, by
``naver_maps``), so region lists and per-district trades are cached in memory.
"""

import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path

import pandas as pd

from housing_app.regions import SEOUL_GU
from housing_app.settings import get_settings

TRADE_CACHE_SIZE = 64


class HousingRepository:
    def __init__(self, path=None):
        self.path = Path(path or get_settings().database_path)
        self._regions = None
        self._trades = OrderedDict()
        self._lock = threading.Lock()  # sync routes run on a thread pool

    def query(self, sql, params=()):
        with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as db:
            return pd.read_sql_query(sql, db, params=params)

    def regions(self):
        if self._regions is None:
            rows = self.query(
                "SELECT DISTINCT sido,sigungu FROM housing_customers ORDER BY sido,sigungu"
            )
            out = {s: sorted(g.sigungu.unique()) for s, g in rows.groupby("sido")}
            out["서울특별시"] = SEOUL_GU
            self._regions = out
        return self._regions

    def scope(self, sido="", sigungu=""):
        clauses = []
        params = []
        for col, value in [("sido", sido), ("sigungu", sigungu)]:
            if value:
                clauses.append(col + "=?")
                params.append(value)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), params

    def summary(self, sido="", sigungu=""):
        where, p = self.scope(sido, sigungu)
        a = self.query(
            "SELECT sido,sigungu,count(*) AS trades,avg(purchase_reference_price) AS avg_price,min(purchase_reference_price) AS min_price,max(purchase_reference_price) AS max_price FROM apartment_trades"
            + where
            + " GROUP BY sido,sigungu",
            p,
        )
        c = self.query(
            "SELECT sido,sigungu,count(*) AS customers,sum(all_original) AS original,sum(all_balance) AS balance FROM housing_customers"
            + where
            + " GROUP BY sido,sigungu",
            p,
        )
        return a.merge(c, on=["sido", "sigungu"], how="outer")

    def customers(self, sido="", sigungu="", customer_id=None):
        where, p = self.scope(sido, sigungu)
        if customer_id is not None:
            where += (" AND " if where else " WHERE ") + "customer_id=?"
            p.append(int(customer_id))
        return self.query(
            "SELECT customer_id,sido,sigungu,apt_name,exclusive_area_m2,purchase_reference_price,estimated_value,all_loan_count,all_original,all_balance FROM housing_customers"
            + where
            + " ORDER BY customer_id",
            p,
        )

    def customer_loans(self, customer_id):
        return self.query(
            "SELECT loan_id,loan_type,loan_purpose,original_principal,outstanding_balance,interest_rate,opened_at,maturity_date,housing_purchase_linked FROM loans_raw WHERE customer_id=? ORDER BY loan_id",
            (int(customer_id),),
        )

    def trades(self, sido, sigungu):
        """Latest-first trades of one district; a copy, so callers may filter freely."""
        key = (sido, sigungu)
        with self._lock:
            cached = self._trades.get(key)
            if cached is not None:
                self._trades.move_to_end(key)
                return cached.copy()
        where, p = self.scope(sido, sigungu)
        frame = self.query(
            "SELECT complex_id,reference_trade_id,apt_name,address,exclusive_area_m2,"
            "purchase_reference_price,estimated_value,reference_deal_date,build_year,"
            "purchase_year FROM apartment_trades"
            + where
            + " ORDER BY reference_deal_date DESC, reference_trade_id",
            p,
        )
        with self._lock:
            self._trades[key] = frame
            if len(self._trades) > TRADE_CACHE_SIZE:
                self._trades.popitem(last=False)
        return frame.copy()

    def complex_loans(self, complex_id):
        return (
            self.query(
                "SELECT count(*) AS customers,sum(all_original) AS original,sum(all_balance) AS balance FROM housing_customers WHERE complex_id=?",
                (complex_id,),
            )
            .iloc[0]
            .to_dict()
        )

    def complex_loans_bulk(self, complex_ids):
        ids = list(dict.fromkeys(complex_ids))
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.query(
            "SELECT complex_id,count(*) AS customers,sum(all_original) AS original,"
            "sum(all_balance) AS balance FROM housing_customers "
            f"WHERE complex_id IN ({placeholders}) GROUP BY complex_id",
            ids,
        )
        found = rows.set_index("complex_id").to_dict("index")
        return {
            complex_id: found.get(complex_id, {"customers": 0, "original": None, "balance": None})
            for complex_id in ids
        }
