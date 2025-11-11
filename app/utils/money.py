# app/utils/money.py
from typing import Union

Number = Union[int, float]

def _thousands(n: int) -> str:
    # 1250200 -> '1.250.200'
    return f"{n:,}".replace(",", ".")

def clp(value: Number | None, trailing: str = ".-") -> str:
    """$1.234.- (sin decimales)"""
    if value is None:
        value = 0
    n = int(round(float(value)))
    return f"${_thousands(n)}{trailing}"

def clp_signed(value: Number | None, trailing: str = ".-") -> str:
    """+/$− con formato $1.234.-"""
    if value is None:
        value = 0
    n = int(round(float(value)))
    sign = "−" if n < 0 else "+"
    return f"{sign}${_thousands(abs(n))}{trailing}"
