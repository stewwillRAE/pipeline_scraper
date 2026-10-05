def year():
    return 2026

def month(file):
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] 
    num = 0
    for i in range(len(months)):
        month = months[i]
        if month in file:
            num = i + 1
    return num