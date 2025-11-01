import datetime

def year_month():
    now = str(datetime.date.today())
    return str(int(now[8:]))

print(year_month())