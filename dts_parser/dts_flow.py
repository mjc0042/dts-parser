import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 1. Get today's date
today = pd.Timestamp.today().normalize()
current_year = today.year
current_month = today.month

# 2. Download all daily data for the current year
# API may have pagination; let's handle approx 250 trading days with page size 500 for safety
BASE_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash'
params = {
    'fields': 'record_date,transaction_today_amt',
    'filter': f'record_calendar_year:eq:{current_year}',
    'sort': 'record_date',
    'page[size]': 500,
    'format': 'json'
}

data = []
page = 1
while True:
    params['page[number]'] = page
    resp = requests.get(BASE_URL, params=params)
    resp.raise_for_status()
    chunk = resp.json()['data']
    if not chunk:
        break
    data.extend(chunk)
    if len(chunk) < int(params['page[size]']):
        break
    page += 1

# 3. Format/prepare DataFrame
df = pd.DataFrame(data)
df['record_date'] = pd.to_datetime(df['record_date'])
# API returns strings; convert to float (may have empty strings)
df['transaction_today_amt'] = pd.to_numeric(df['transaction_today_amt'], errors='coerce').fillna(0)

# Sum over all categories for each day (should already be 1 row/day, but we group in case)
daily = df.groupby('record_date')['transaction_today_amt'].sum().sort_index()

# 4. Get today/month-to-date/year-to-date values
today_str = today.strftime('%Y-%m-%d')
if today in daily.index:
    today_value = daily.loc[today]
else:
    today_value = None
    print(f"Warning: No data found for today {today_str}.")

# Month-to-date: from 1st of month to today
mtd = daily[(daily.index >= pd.Timestamp(current_year, current_month, 1)) &
            (daily.index <= today)].sum()

# Year-to-date: from Jan 1st to today
ytd = daily[(daily.index >= pd.Timestamp(current_year, 1, 1)) &
            (daily.index <= today)].sum()

# Calculate ratios (guard against zero division)
pct_today_ytd = (today_value / ytd * 100) if today_value is not None and ytd > 0 else None
pct_mtd_ytd = (mtd / ytd * 100) if ytd > 0 else None

# 5. Calculate and graph daily percent change (% change from previous day)
pct_change = daily.pct_change() * 100

# 6. Output
print(f'Operating Cash Deposits & Withdrawals (total, all categories):')
print(f'Data up to: {today_str}')
print(f"Today's value:     ${today_value:,.0f}" if today_value is not None else "Today's value:     Data not available.")
print(f"Month-to-date:     ${mtd:,.0f}")
print(f"Year-to-date:      ${ytd:,.0f}")
print(f"% Today / YTD:     {pct_today_ytd:.3f}%" if pct_today_ytd is not None else "% Today / YTD:     N/A")
print(f"% Month / YTD:     {pct_mtd_ytd:.3f}%" if pct_mtd_ytd is not None else "% Month / YTD:     N/A")

# 7. Plot
plt.figure(figsize=(12, 6))
plt.plot(pct_change.index, pct_change.values)
plt.title(f'Daily % Change in Deposits & Withdrawals (All Categories) for {current_year}')
plt.xlabel('Date')
plt.ylabel('Daily % Change')
plt.grid(True)
plt.tight_layout()
plt.show()
