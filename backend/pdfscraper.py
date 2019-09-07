from tika import parser
import collections as Counter
import os
import sys
import calendar
import json

# defines the currency symbol (i.e. dollars for Australia)
currency = '$'
# defines which words to look for in the line, 'due' seems to work well for all 3 bills (and the EE bill as well)
keywords_amount = ['due']
keywords_period_months = [' jan ', ' feb ', ' mar ', ' apr ', ' may ', ' jun ', ' jul ', ' aug ', ' sep ', ' oct ', ' nov ', ' dec ']
keywords_period = ['period']
period_sep = [' - ', ' to ']
keywords_usage = ['kwh']
keywords_usage_not = ['c/kwh']
keywords_usage_types = ['shoulder', 'off peak', 'off-peak', 'controlled load', 'peak']
keywords_distributor = ['power failure']
keywords_distributor_2 = ['call', '24 hrs']
keywords_discounts = ['%', 'discount']
keywords_discounts_types = ['usage', 'total bill', 'overall', 'supply']
states = ["QLD", "ACT", "NSW", "VIC", "SA", "WA", "TAS", "NT"]
keywords_postcode_verify = ['Service address']
keywords_postcode_verify_2 = ['your electricity bill']
# reads PDF file from terminal parameters (for example you'd call the script as follows: 'python pdfscraper.py [pdf file name here without the brackets]')
# this is made to allow for the code to be called following a request from the front-end
'''
pathParts = []
for i in range(len(sys.argv)-1):
    pathParts.append(sys.argv[i+1])
path = " ".join(pathParts)
if not os.path.isfile(path):
    print("Please enter a valid path to the PDF")
    exit()
'''
            
def extractData(path):
    raw = parser.from_file(path)
    contents = (raw['content'])
    lines = contents.splitlines()
    amount = getBillAmount(lines)
    period = getPeriod(lines)
    periodDays = periodtoDays(period)
    usages = getUsage(lines)
    distributor = getDistributor(lines)
    discounts = getDiscounts(lines)
    postcode = getPostcode(lines)
    data = {
        "amount": amount,
        "period": periodDays,
        "usages": usages,
        "discounts": discounts,
        "distributor": distributor,
        "postcode": postcode
    }
    return data

def getPostcode(lines):
    postcode = None
    try:
        for i in range(len(lines)):
            line = lines[i]
            for cstate in states:
                if cstate in line:
                    for verify in keywords_postcode_verify:
                        if verify in line:
                            postcode = line.split()
                            postcode = int(postcode[len(postcode)-1])
                    if not postcode:
                        for verify in keywords_postcode_verify_2:
                            if verify in lines[i-1].lower():
                                postcode = lines[i].split()
                                postcode = int(postcode[len(postcode)-1])
    except ValueError:
        print("error")
    return postcode


def getDiscounts(lines):
    discounts = []
    for i in range(len(lines)):
        check = False
        line = lines[i]
        for j in keywords_discounts:
            if j in line.lower():
                if check:
                    for dtype in keywords_discounts_types:
                        if dtype in line.lower():
                            amount = None
                            try:
                                for percent in line.lower().split():
                                    if "%" in percent:
                                        amount = percent
                                if len(amount.split("cr")) > 1:
                                    amount = float(amount.split("cr")[1].split("%")[0])
                                elif len(amount.split("(")) > 1:
                                    amount = float(amount.split("(")[1].split(")")[0].split("%")[0])
                                else:
                                    amount = float(amount.split("%")[0])
                                disq = False
                                for discount in discounts:
                                    if amount == discount['amount']:
                                        disq = True
                                if not disq:
                                    discounts.append({
                                        "type": dtype.title(),
                                        "amount": amount
                                    })
                            except ValueError:
                                pass
                else:
                    check = True
    return discounts


def getDistributor(lines):
    dist = None
    for i in range(len(lines)):
        for j in keywords_distributor:
            if dist:
                break
            if j in lines[i].lower():
                dist = lines[i+1]
                if not len(dist.split()):
                    dist = None
                else:
                    dist = dist.split()[0]
    if not dist:
        for i in range(len(lines)):
            check = False
            for j in keywords_distributor_2:
                if dist:
                    break
                if j in lines[i].lower():
                    if check:
                        dist = lines[i].split()
                        dist = " ".join(dist[1:3])
                    else:
                        check = True
    return dist



def getUsage(lines):
    usages = [] 
    for i in range(len(lines)):
        line = lines[i].lower()
        check = False
        for j in keywords_usage:
            if j in line:
                check = True
                break
        if check:
            check = False
            found = False
            for j in keywords_usage_types:
                if j in line:
                    found = True
                    usages.append({
                        "type": j.title(),
                        "desc": line,
                        "amount": None,
                        "cost": None
                    })
            if not found:
                for j in keywords_usage_types:
                    if j in lines[i-2].lower():
                        found = True
                        usages.append({
                            "type": j.title(),
                            "desc": line,
                            "amount": None,
                            "cost": None
                        })
    for usage in usages:
        cost = None
        for i in range(len(usage['desc'].split())):
            word = usage['desc'].split()[i]
            for keyword in keywords_usage:
                if keyword in word.lower():
                    disq = False
                    for checkword in keywords_usage_not:
                        if checkword in word.lower():
                            disq = True
                    try:
                        if not disq:
                            value = float(usage['desc'].split()[i-1])
                            cost = float(usage['desc'].split()[i+1][1:])*100
                        else:
                            value = float(usage['desc'].split()[i-2])
                            cost = float(usage['desc'].split()[i-1])
                        dup = False
                        for cvalue in usages:
                            cvalue = cvalue['amount']
                            if value == cvalue:
                                dup = True
                        if not dup:
                            usage['amount'] = value
                            usage['cost'] = cost
                    except ValueError:
                        pass
    for usage in usages[:]:
        if usage['amount'] and usage['cost']:
            usage.pop('desc', None)
        else:
            usages.remove(usage)

    for usage in usages:
        for usage2 in usages:
            if not usage == usage2:
                if usage['cost'] == usage2['cost'] and usage['type'] == usage2['type']:
                    usage['amount'] += usage2['amount']
                    usages.remove(usage2)
    return usages


def periodtoDays(period):
    first, second = period
    startmonth = list(calendar.month_abbr).index(first[1].title()) 
    endmonth = list(calendar.month_abbr).index(second[1].title())
    startday = int(first[0])
    startyear = int(first[2])
    endday = int(second[0])
    endyear = int(second[2])
    days = 0
    while (not startmonth == endmonth) or (not startyear == endyear):
        '''print(startmonth, startyear, endmonth, endyear)
        print()'''
        _, numDays = calendar.monthrange(startyear, startmonth)
        days += numDays - startday + 1
        if startmonth == 12:
            startyear += 1
            startmonth = 1
        else:
            startmonth += 1
        startday = 1
    days += endday
    return days

def getPeriod(lines):
    period = None
    for i in lines:
        check1 = False
        check2 = False
        for j in keywords_period:
            if j in i.lower():
                check2 = True
        for j in keywords_period_months:
            if j in i.lower():
                if check1 and check2:
                    period = i.lower()
                    check1 = False
                    check2 = False
                else:
                    check1 = True
    if period:
        active = False
        mid = False
        first = []
        second = []
        for i in range(len(period.split())):
            if not active:
                for j in keywords_period:
                    if j in period.split()[i]:
                        active = True
            elif active:
                for j in range(3):
                    first.append(period.split()[i+j])
                    second.append(period.split()[i+j+4])
                break
        if len(first[2]) == 2:
            first[2] = "20"+first[2]
            second[2] = "20"+second[2]
        period = (first, second)
    return period

# the function that extract the amount from the PDF
def getBillAmount(lines):
    amount = None
    for i in lines:
        # search for keywords inside each line
        for j in keywords_amount:
            if j in i:
                # when a keyword is found inside a line, the line is split into words
                pline = i.split()
                # each word is searched separately for the currency symbol
                for i in pline:
                    if currency in i:
                        # when the currency symbol is found we try to parse the word (without the symbol) into a float
                        try:
                            amount = float(i[1:])
                        except ValueError:
                            continue
    return amount

'''
def validateAmount(billdata):
    usageCharge = 0
    for usage in billdata['usages']:
        usageCharge += usage['amount'] * (usage['cost'] / 100)
    for discount in discounts:
        if discount['type'] == "Usage":
            usageCharge *= (discount['amount'] / 100)
        elif discount['type'] == "Overall":
'''

'''
data = extractData(path)
amount = data['amount']
period = data['period']
usages = data['usages']
distributor = data['distributor']


# if the function couldn't find the amount the returned 'amount' variable will be of type None, the code below is just to demonstrate the results, in the final build,
# the prints will be removed and a call to the script that scrapes the website will be made to get the lowest pricing
if amount:
    print("Amount found is: %s%.2f" %(currency, amount))
else:
    print("Amount not found in PDF")

if period:
    print("This bill spans: %d days" %(period))
else:
    print("Period not found")

for usage in usages:
    print(usage)

if distributor:
    print("Distributor: %s" %(distributor))
else:
    print("Distributor not found")

costPerDay = amount/period
print("Cost per day: %s%.3f\nEstimated yearly cost: %s%.2f" %(currency, costPerDay, currency, costPerDay*365))
data['costPerDay'] = float("{0:.2f}".format(costPerDay))
data['yearlyEstimate'] = float("{0:.2f}".format(costPerDay*365))

print()
print(json.dumps(data, indent=4))'''