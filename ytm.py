# download the csv data from - https://www.nseindia.com/market-data/bonds-traded-in-capital-market
# reset the column names to SYMBOL,SERIES,ISIN,COUPON RATE,FACE VALUE,LTP,CHG,volume,value,CREDIT RATING AGENCY,CREDIT RATING,MATURITY DATE
# rename the file to bonds.csv
# run below
# from output you have to do some cleaning like adjusting face value and recent market changes like face value reduction, etc

import numpy as np
from datetime import datetime
import pandas as pd
import math


def calculate_ytm(price, face_value, coupon_rate, years_to_maturity, frequency=12, guess=0.05):
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

    return ytm * 100


def years_to_maturity(maturity_date_str):
    """
    Convert today's date to maturity date difference in years
    
    maturity_date_str format: YYYY-MM-DD
    """

    today = datetime.today()
    maturity_date = datetime.strptime(str(maturity_date_str), "%Y-%m-%d")

    days_difference = (maturity_date - today).days

    years = days_difference / 365.25  # accounts for leap years

    return years

# Example
price = 105999
face_value = 100000
coupon_rate = 9.3
maturity_date_str = '2034-05-09'


ytm = calculate_ytm(price, face_value, coupon_rate, years_to_maturity(maturity_date_str))

print("YTM:", round(ytm * 100, 2), "%")

def process_bond_data(input_file, output_file):
    # Load the CSV file
    df = pd.read_csv(input_file)
    df['MATURITY DATE'] = pd.to_datetime(df['MATURITY DATE'], dayfirst=True, errors='coerce').dt.date
    cols_to_cast = ['COUPON RATE', 'FACE VALUE', 'LTP']
    for col in cols_to_cast:
        if df[col].dtype == 'str':
            df[col] = df[col].str.replace(r'[^\d.]', '', regex=True)
        
        # This converts to float and marks errors as NaN
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)


    print(df.dtypes)
    print(df)
    required_cols = ['COUPON RATE', 'FACE VALUE', 'LTP', 'MATURITY DATE']
    df = df.dropna(subset=required_cols)
    
    # Apply the ytm function to each row
    # It passes the specific columns required by your function
    df['YTM'] = df.apply(lambda row: calculate_ytm(
        row['LTP'],	
        row['FACE VALUE'], 
        row['COUPON RATE'], 
        years_to_maturity(row['MATURITY DATE'])
    ), axis=1)
    df['YTM'] = df['YTM'].astype(str) + '%'

    # Save the updated dataframe to a new CSV
    df.to_csv(output_file, index=False)
    print(f"File saved successfully as {output_file}")

# Run the processing
process_bond_data('bonds.csv', 'bonds_with_ytm.csv')

