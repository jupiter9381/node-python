import os
import sys
import calendar
import json
import numpy as np
import datetime
from pdfscraper import periodtoDays
from multiprocessing.dummy import Pool as ThreadPool

def getBestPlan(subplans, bill):
    pool = ThreadPool(len(subplans))
    cplans = []
    for company in subplans:
        for plan in subplans[company]:
            if not (type(plan) == bool):
                plan['company'] = company
                cplans.append(plan)
    subplans = list(filter(bool, cplans))
    datalist = []
    for plan in subplans:
        datalist.append({
            "plan": plan,
            "company": plan['company'],
            "bill": bill
        })
    results = pool.map(getEstimate, datalist)
    results = list(filter(bool, results))
    lowest = np.Inf
    cheapestPlan = None
    cheapestPlanC = None
    for result in results:
        plan, company, charge = result
        if charge < lowest:
            lowest = charge
            cheapestPlan = plan
            cheapestPlanC = company
    lowest = float("{0:.2f}".format(lowest))
    return ({
        "plan": cheapestPlan,
        "postcode": bill['postcode'],
        "company": cheapestPlanC,
        "estimate": lowest})

def getEstimate(datalist):
    bill = datalist['bill']
    company = datalist['company']
    plan = datalist['plan']
    usages = bill['usages']
    year = datetime.datetime.now().year
    weekends = getDayCountYear(year, "Sat") + getDayCountYear(year, "Sun")  
    yeardays = None
    if calendar.isleap(year):
        yeardays = 366
    else:
        yeardays = 365
    totalUsage = 0
    for usage in usages:
        totalUsage += usage['amount']
    supplyCharge = None
    usageCharge = 0
    if plan:
        #print(plan["ID"])
        for charge in plan['priceSummary']['generalCharges']:
            if charge['name'] == "Daily supply charge":
                if 'value' in charge:
                    supplyCharge = (charge['value'] / 100) * yeardays
                    supplyCharge = float("{0:.2f}".format(supplyCharge))
                elif 'minValue' in charge:
                    supplyCharge = ((charge['minValue']/100) * yeardays + (charge['maxValue'] / 100) * yeardays)/2
            elif charge['name'] == "General usage rates":
                pricing = (charge['value']/100) * totalUsage
                usageCharge = float("{0:.2f}".format(pricing))
            elif charge['name'] == "Time of use usage rates":
                if 'value' in charge:
                    usageCharge = (charge['value'] / 100) * totalUsage
                    usageCharge = float("{0:.2f}".format(usageCharge))
                elif 'minValue' in charge:
                    for period in plan['priceSummary']['timeOfUseCharges']:
                        first, second= period['period'].split('-')
                        first = first.split()
                        second = second.split()
                        year = str(year)
                        if list(calendar.month_abbr).index(first[1].title()) > list(calendar.month_abbr).index(second[1].title()):
                            second.append(year)
                            first.append((int(year)-1))
                        else:
                            first.append(year)
                            second.append(year)
                        first[1] = first[1].lower()
                        second[1] = second[1].lower()
                        days = periodtoDays((first, second))
                        partofyear = days/yeardays
                        perioddays = None
                        if period['weekdays'] == "Mon-Fri":
                            perioddays = yeardays - weekends
                        elif period['weekdays'] == "Weekends":
                            perioddays = weekends
                        partofyear = partofyear * (perioddays/yeardays)
                        for timing in period['details']:
                            for currentUsage in usages:
                                if currentUsage['type'].lower() == timing['usageType'].lower():
                                    currentUsage['calculated'] = partofyear * currentUsage['amount']
                                    #print("\t Type: %s, %s Amount: %d, Part: %.2f, Price: %.2f, Estimate: %.2f, Used up: %.2f" %(currentUsage['type'], timing['usageType'], currentUsage['amount'], partofyear, timing['price'], (currentUsage['amount']*(timing['price']/100)*partofyear), currentUsage['calculated']))
                                    usageCharge += (currentUsage['amount']*(timing['price']/100)*partofyear)
                                    break

                    #usageCharge = ((charge['minValue']/100) * 365 + (charge['maxValue'] / 100) * 365)/2
    totalCharge = None
    #if supplyCharge and usageCharge:
    #    print("%s Supply Charge: $%.2f and Usage Charge: $%.2f = $%.2f" %(plan['ID'], supplyCharge, usageCharge, supplyCharge+usageCharge))
    if not supplyCharge or not usageCharge:
        print("Error with plan: "+plan['ID'])
    try:
        totalCharge = supplyCharge + usageCharge
    except:
        print(supplyCharge, usageCharge)
    return (plan, company, totalCharge)


def getDayCountYear(year, day):
    dayc = 52
    if calendar.isleap(year):
        if (datetime.datetime(year, 1, 1).strftime("%a").lower() == day.lower()) or (datetime.datetime(year, 1, 2).strftime("%a").lower() == day.lower()) :
            dayc+=1
    else:
        if (datetime.datetime(year, 1, 1).strftime("%a").lower() == day.lower()):
            dayc+=1
    return dayc