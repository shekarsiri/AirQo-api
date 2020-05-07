from datetime import datetime

def convert_date_to_formated_str(date,frequency):
    """
    Converts datetime to a string basing on the frequency passed.
    """
    if frequency == 'monthly':
        return datetime.strftime(date,'%B %Y')
    elif frequency == 'daily':
         return datetime.strftime(date,'%Y-%m-%d')
    else:
        return datetime.strftime(date,'%Y-%m-%d %H:%M') 

def date_to_formated_str(date):
    """
    Converts datetime to a string
    """
    return datetime.strftime(date,'%Y-%m-%d %H:%M')

def str_to_date(st):
    """
    Converts a string to datetime
    """
    return datetime.strptime(st, '%Y-%m-%dT%H:%M:%S.%fZ')

def date_to_str(date):
    """
    Converts datetime to a string
    """
    return datetime.strftime(date,'%Y-%m-%dT%H:%M:%S.%fZ')
    
def str_to_date_find(st):
    """
    Converts a string of different format to datetime
    """
    return datetime.strptime(st, '%Y-%m-%dT%H:%M:%SZ')

def generate_datetime(date, time):
    if date == None or date == "":
        return None
    else:
        if time==None or time=="":
            time ="00:00"
        date_time = date+"T"+time+":00Z"
        return date_time

def set_pm25_category_background(pm25_conc_value):
    category_color = ""    
    if pm25_conc_value >0.0 and pm25_conc_value <=12.0:
        category_color = '#45e50d'
    elif pm25_conc_value >12.0 and pm25_conc_value <=35.4:
        category_color = '#f8fe28'
    elif pm25_conc_value > 35.4 and pm25_conc_value <= 55.4:
        category_color = '#ee8310'
    elif pm25_conc_value > 55.4 and pm25_conc_value <= 150.4:
        category_color = '#fe0000'
    elif pm25_conc_value > 150.4 and pm25_conc_value <= 250.4:
        category_color = '#8639c0'
    elif pm25_conc_value > 250.4 and pm25_conc_value <=500.4:
        category_color = '#81202e'
    else:
        category_color = '#808080'

    return category_color
