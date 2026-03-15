import numpy as np
from datetime import datetime

def calculate_ytm(price, face_value, coupon_rate, years_to_maturity, frequency=1, guess=0.05):
    """
    Calculate Yield to Maturity (YTM)

    Parameters
    ----------
    price : float
        Current bond price
    face_value : float
        Face value of the bond
    coupon_rate : float
        Annual coupon rate
    years_to_maturity : int
        Years until bond maturity
    frequency : int
        Coupon payments per year (1=annual, 2=semiannual, etc.)
    guess : float
        Initial guess for YTM

    Returns
    -------
    float
        Yield to maturity (annual)
    """

    periods = years_to_maturity * frequency
    coupon = face_value * coupon_rate / (frequency * 100)

    import math

    def bond_price(ytm, periods, coupon, face_value, frequency):
        total = 0.0

        full_periods = int(math.floor(periods))
        fractional_period = periods - full_periods

        # Full coupon payments
        for t in range(1, full_periods + 1):
            total += coupon / (1 + ytm / frequency) ** t

        # Fractional last coupon if needed
        if fractional_period > 0:
            t = full_periods + fractional_period
            total += coupon * fractional_period / (1 + ytm / frequency) ** t

        # Face value discounted using exact maturity
        total += face_value / (1 + ytm / frequency) ** periods

        return total


    ytm = guess

    for _ in range(1000):
        price_est = bond_price(ytm,periods, coupon, face_value, frequency)
        derivative = (bond_price(ytm + 1e-6, periods, coupon, face_value, frequency) - price_est) / 1e-6
        ytm -= (price_est - price) / derivative

    return ytm


def years_to_maturity(maturity_date_str):
    """
    Convert today's date to maturity date difference in years
    
    maturity_date_str format: YYYY-MM-DD
    """

    today = datetime.today()
    maturity_date = datetime.strptime(maturity_date_str, "%Y-%m-%d")

    days_difference = (maturity_date - today).days

    years = days_difference / 365.25  # accounts for leap years

    return years

# Example
price = 982.55
face_value = 1000
coupon_rate = 10.9
maturity_date_str = '2026-06-13'
frequency = 12

ytm = calculate_ytm(price, face_value, coupon_rate, years_to_maturity(maturity_date_str), frequency)

print("YTM:", round(ytm * 100, 2), "%")
