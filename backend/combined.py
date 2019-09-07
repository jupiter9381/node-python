import requests
import json
import sys
import numpy as np
from bs4 import BeautifulSoup
import bs4
from multiprocessing.dummy import Pool as ThreadPool 
from threading import Thread
from urllib import request, parse
import queue
import time

# this is just a placeholder for the postcode
try:
    # postcode as string
    postcode = str(2000)
except IndexError:
    print("Enter a postcode")
    exit()

# kWh usage per day, for Energy Australia, set to 10.8333 kWh per day by default to have roughly the same results as the other 2 companies as they both assume medium consumption
usagePerDay = 10.83333333333333334
try:
    # number of months per bill, i.e. 1 for monthly, 2 for bi-monthly, 3 for quarterly, 12 for yearly, etc.
    period = 12
except IndexError:
    print("Enter a period in months")
    exit() 
except ValueError:
    print("Period must be an integer number")
# list of Australian states, used for figuring out the addresses from postcodes
states = ["QLD", "ACT", "NSW", "VIC", "SA", "WA", "TAS", "NT"]

# plans are stored in the 'plans' list until they're compared
allPlans = []
comparedPlans = {}

# three functions, one for each company, all have the same workflow and output with some differences
def getMainEnergyAustralia(que):
    global postcode, usagePerDay, period, allPlans
    apiEnergyAustralia='https://www.energyaustralia.com.au/qt2/app/plans/search?customerType=RES&meterExchange=false&movingHouse=false&postcode='+postcode+'&qualifications=&safetyQuestions=NA'
    r = requests.get(apiEnergyAustralia)
    if r.status_code == 200:
        rjson = r.json()
        if not rjson['electricityPlans']:
            print("No results from Energy Australia")
            return True
        else:
            for i in rjson['electricityPlans']:
                name = i['name']
                distributor = i['distributor']['distributor']
                rates = i['rates']
                discount = rates['discountPercent']
                supplyRate = rates['supply']['baseRate']
                usageRate = rates['usage'][0]['values'][0]['baseRate']
                periodDays = period * 30
                costPerDay = ((usagePerDay * usageRate) / 100) + supplyRate
                cost = periodDays * costPerDay
                if discount > 0:
                    cost = cost * (1 - (discount / 100))
                cost = float("{0:.0f}".format(cost))
                usage = usagePerDay * periodDays
                usage = int("{0:.0f}".format(usage))
                pricePerkWh = float("{0:.2f}".format((cost/usage) * 100))
                plan = {
                    'company': 'Energy Australia',
                    'name': name,
                    'cost': cost,
                    'usage': usage,
                    'pricePerkWh': pricePerkWh,
                    'discount': discount,
                    'distributor': distributor
                }
                que.put(plan)
        return True
    else:
        return False

def getMainOriginEnergy(que):
    global postcode, usagePerDay, period, allPlans
    apiOriginEnergy = 'https://salesplan-api-prod.api.origindigital-pac.com.au/api/v1/plans?customerType=residential&searchByPostcode=true&postcode='+postcode+'&fuelType=electricity&hasSolarPanels=false&connectionScenario=PROS_SWT'
    r = requests.get(apiOriginEnergy)
    if r.status_code == 200:
        rjson = r.json()
        if not rjson['data']['plans']:
            print("No results from Origin Energy")
            return True
        else:
            for i in rjson['data']['plans']:
                planj = i['fuel']['electricity']['energyCost']['medium']['0']
                periodToYear = period/12
                cost = planj['approxCharge'] * periodToYear
                cost = float("{0:.0f}".format(cost))
                usage = planj['granularConsumption'] * periodToYear
                usage = int("{0:.0f}".format(usage))
                pricePerkWh = float("{0:.2f}".format((cost/usage) * 100))
                discount = planj['refPercentSaving']
                name = i['title']
                distributor = i['fuel']['electricity']['tariff'][0]['serviceProviderName']
                plan = {
                    'company': 'Origin Energy',
                    'name': name,
                    'cost': cost,
                    'usage': usage,
                    'pricePerkWh': pricePerkWh,
                    'discount': discount,
                    'distributor': distributor
                }
                que.put(plan)
        return True
    else:
        return False


def getMainAGL(que):
    global postcode, usagePerDay, period, allPlans
    state, suburb = getAddress()
    apiAGL = 'https://product.api.agl.com.au/v1/personalised/experiment1?houseNumber=1&unitNumber=1&streetNumber=1&streetName=1&streetType=1&suburb='+suburb+'&state='+state+'&postcode='+postcode+'&deliveryPointId=42713832&fuelType=Dual&customerType=Residential&customerSituation=LivingHere&isExistingCustomer=false'
    header = {'X-Correlation-ID': '326A9DEF-431D-4DF9-4461-6B9C48A00284'}
    r = requests.get(apiAGL, headers=header)
    if r.status_code == 200:
        rjson = r.json()
        if not rjson['electricity']['products']:
            print("No results from AGL")
        else:
            planj = rjson['electricity']['products']
            periodToYear = period/12
            for i in planj:
                for j in i['referencePriceList']:
                    if j['tariffDescription'] == "Single Rate":
                        name = j['energyPlanName']
                        distributor = j['distributionZone']
                        cost = j['lowestPriceAllDiscount']
                        cost = cost[1:]
                        cost = float("".join(cost.split(','))) * periodToYear
                        cost = float("{0:.2f}".format(cost))
                        usage = float(j['peak']) * periodToYear
                        pricePerkWh = float("{0:.2f}".format((cost/usage) * 100))
                        discount = j['percentageOfReferencePrice']
                        if discount[1] == '%':
                            discount = discount[0]
                        else:
                            discount = discount[:2]
                        discount = float(discount)
                        plan = {
                            'company': 'AGL',
                            'name': name,
                            'cost': cost,
                            'usage': usage,
                            'pricePerkWh': pricePerkWh,
                            'discount': discount,
                            'distributor': distributor
                        }
                        que.put(plan)
        return True
    else:
        return False


def getMainDodoFixed(que):
    global postcode
    requestBody = {"postcode":postcode,"hasConcession":"false","averageMonthlySolarExport":"null","meterConfigCode":"null","solarPlanTypeId":"null"}
    urlDodo = "https://signup-api.iprimus.com.au/api/energy/Availability"



# this function is different from the other 3 companies, here we don't use an API but instead we scrape the webpage
def getMainDodo(que):
    global postcode, usagePerDay, period, allPlans
    urlDodo = 'https://www.energymadeeasy.gov.au/offer/928548/print?postcode='+postcode
    page = requests.get(urlDodo)
    if page.status_code == 200:
        soup = BeautifulSoup(page.text, 'html.parser')
        usage_tags = soup.find_all(class_='data')
        cost_tags = soup.find_all(class_='value')
        contractTable = soup.find_all(class_='panel__table panel__table--no-bottom')[1]
        distributorRow = contractTable.find_all('td')
        distributorRow = distributorRow[len(distributorRow)-1]
        distributor = distributorRow.contents[0].strip()
        periodDays = period * 30
        for i in range(len(cost_tags)):
            try:
                cost = float("".join(cost_tags[i].contents[0].split(',')))
                usage = float(usage_tags[i].find_all('div')[1].contents[0].split()[0])
            except ValueError:
                return False
            usage = float("{0:.0f}".format(usage * periodDays))
            pricePerkWh = float("{0:.2f}".format((cost/usage) * 100))
            plan = {
                'company': 'Dodo',
                'name': 'N/A',
                'cost': cost,
                'usage': usage,
                'pricePerkWh': pricePerkWh,
                'discount': '0',
                'distributor': distributor
            }
            que.put(plan)
        return True
    else:
        return False

# function that compares all plans and retrieves the cheapest one
def getMainPlans(newPostcode=None):
    global comparedPlans, allPlans, postcode
    comparedPlans = {}
    start = time.time()
    if newPostcode:
        postcode = str(newPostcode)
    if not checkPostcode():
        return {'error': "Invalid postcode"}
    que = queue.Queue()
    AGL = Thread(target=getMainAGL, args=[que])
    Dodo = Thread(target=getMainDodo, args=[que])
    EnergyAustralia = Thread(target=getMainEnergyAustralia, args=[que])
    OriginEnergy = Thread(target=getMainOriginEnergy, args=[que])
    AGL.start()
    Dodo.start()
    EnergyAustralia.start()
    OriginEnergy.start()
    AGL.join()
    Dodo.join()
    EnergyAustralia.join()
    OriginEnergy.join()
    minimum = np.Inf
    minindexPerkWh = None
    allPlans = []
    while not que.empty():
        allPlans.append(que.get())
    for i in range(len(allPlans)):
        if allPlans[i]['pricePerkWh'] < minimum:
            minimum = allPlans[i]['pricePerkWh']
            minindexPerkWh = i
    minimum = np.Inf
    minindexCost = None
    for i in range(len(allPlans)):
        if allPlans[i]['cost'] < minimum:
            minimum = allPlans[i]['cost']
            minindexCost = i
    comparedPlans['cheapestPerkWhPlan'] = allPlans[minindexPerkWh]
    comparedPlans['cheapestPerCostPlan'] = allPlans[minindexCost]
    comparedPlans['allPlans'] = allPlans
    print("Executed in %.0f seconds" %(time.time()-start))
    return comparedPlans


# function that retrieves the address from the given postcode
def getAddress():
    global postcode, states
    apiGoogle = "https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=eg&q="+postcode+" australia"
    google = requests.get(apiGoogle)
    state = None
    line = None
    suburb = None
    if google.status_code == 200:
        gtext = google.text.split(',')
        found = False
        for i in gtext:
            if found:
                break
            for j in states:
                if j in i:
                    state = j
                    line = i
                    found = True
                    break
        if not line:
            return False
        line = line.split()
        suburb = []
        for i in range(len(line)):
            if not state in line[i] and not postcode in line[i]:
                suburb.append(line[i])
        suburb = " ".join(suburb)[1:]
    else:
        return False
    return (state, suburb)


# when this function is called it uses a global postcode to get all electricity subplans for that postcode provided by the Origin Energy company
def getOriginEnergy(queue):
    global postcode
    url = 'https://factsheets-api-prod.api.origindigital-pac.com.au/api/v1/getbpidproducts?customerType=residential&postcode='+postcode+'&divisionId=01&elecGreenPercentage=0'
    r = requests.get(url)
    if r.status_code == 200:
        if len(r.json()['results']) > 0:
            pool = ThreadPool(len(r.json()['results'])) 
            urls = []
            for i in r.json()['results']:
                urls.append(i['elecInfo']['url'])
            results = pool.map(extractEnergyMadeEasy, urls)
            results = list(filter(bool, results))
            result = {}
            result['OriginEnergy'] = results
            queue.put(result)
        else:
            return False
    else:
        return False


# when this function is called it uses a global postcode to get all electricity subplans for that postcode provided by the AGL company
def getAGL(queue):
    global postcode
    url = 'https://www.agl.com.au/_api/FactSheet/DisplayEPFSResult'
    headers = {
        'Host': 'www.agl.com.au',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.agl.com.au/help/rates-contracts/energy-price-fact-sheets?Postcode=2000&CustomerType=Residential&FuelType=Electricity&TariffType=Unknown&Plan=AGLMKTRE2420001',
        'X-NewRelic-ID': 'UwMEWFNUGwQIVFFXBgEE',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Length': '129',
        'Connection': 'keep-alive',
        'Cookie': 'SC_ANALYTICS_GLOBAL_COOKIE=611a20207bf14802a1bf1a0aa6e671be|False; utag_main=v_id:016bdc759508002038cb898729520104d001700d00bd0$_sn:13$_se:20$_ss:0$_st:1563565803187$vapi_domain:agl.com.au$ses_id:1563563584017%3Bexp-session$_pn:3%3Bexp-session; AMCV_E41E7DBD59955C940A495CFD%40AdobeOrg=-1303530583%7CMCIDTS%7C18088%7CMCMID%7C49780184467898722783837924195017637487%7CMCAID%7CNONE%7CMCOPTOUT-1562779022s%7CNONE%7CvVersion%7C3.3.0; channel_stacking=dir|oth|dir; s_ecid=MCMID%7C49780184467898722783837924195017637487; s_getNewRepeat=1563564014892-Repeat; s_lastvisit=1563564014893; s_lastvisit_s=Less%20than%207%20days; s_ppn=agl%3Amain%3Ahelp%3Arates-contracts%3Aenergy-price-fact-sheets; AMCV_E41E7DBD59955C940A495CFD%40AdobeOrg=-1303530583%7CMCIDTS%7C18097%7CMCMID%7C49780184467898722783837924195017637487%7CMCAID%7CNONE%7CMCOPTOUT-1563571203s%7CNONE%7CvVersion%7C3.3.0; deviceDimensions={"Width":1920,"Height":1080}; isMobileDevice=false; AMCVS_E41E7DBD59955C940A495CFD%40AdobeOrg=1; check=true; mbox=session#46e5260d63694931beeddbfb1416e763#1563565445; s_ppvl=https%253A%2F%2Fwww.agl.com.au%2Fget-connected%2Felectricity-gas-plans%253Fcidi%253Dhp-ql-cp%2523%2F%2C86%2C86%2C3312%2C1920%2C966%2C1920%2C1080%2C1%2CP; s_ppv=agl%253Amain%253Ahelp%253Arates-contracts%253Aenergy-price-fact-sheets%2C46%2C46%2C1633%2C1920%2C615%2C1920%2C1080%2C1%2CP; s_cc=true; ASP.NET_SessionId=ivpstuvdwshe1ysgjvnulitp; s_sq=%5B%5BB%5D%5D; KP_UID=0e45d815-bcf3-2a2b-9ba9-0b3b753058ce; delaconsessid=5960e1f1e4dc4aa48506b401ff72acb2; delaconphonenums=39199,1300 716 516,true,131 245,au,|; __dasct=1563563608278; __dalvt=1563563608278; agl-qas-selected-address=%7B%22AddressMoniker%22%3A%7B%22Moniker%22%3A%22AUE%7C2d079ee2-9430-4ce3-8b79-a2038502c95f%7C7.730zOAUEHgXjBwAAAAAIAgEAAAAAoUXYwAAAAAAAAAAA..9kAAAAAP....8AAAAAAAAAAAAAAAAAAABQZWFraHVyc3QAAAAAAA--%249%22%2C%22PartialAddress%22%3A%22Peakhurst%20West%20School%2C%20121%20Belmore%20Road%2C%20PEAKHURST%20%20NSW%20%202210%22%7D%2C%22SelectedAddressDetails%22%3A%7B%22SearchResponse%22%3A%7B%22CareOf%22%3Anull%2C%22UnitNumber%22%3A%22%22%2C%22HouserNumber%22%3A%22121%22%2C%22Street%22%3A%22Belmore%20Road%22%2C%22StreetName%22%3A%22Belmore%22%2C%22StreetType%22%3A%22Road%22%2C%22PostCode%22%3A%222210%22%2C%22State%22%3A%22NSW%22%2C%22Floor%22%3A%22%22%2C%22Suburb%22%3A%22PEAKHURST%22%2C%22AddressType%22%3A%22S%22%2C%22POBoxNumber%22%3A%22%22%2C%22POBoxType%22%3A%22%22%2C%22DPID%22%3A%2284328677%22%2C%22Latitude%22%3A%22-33.96198136%22%2C%22Longitude%22%3A%22151.04945354%22%2C%22ValidatedByQAS%22%3A%22X%22%2C%22AddressMode%22%3Anull%2C%22MosaicGroup%22%3Anull%2C%22MosaicType%22%3Anull%7D%2C%22SelectedAddress%22%3A%22%20%20121%20Belmore%20Road%20%20PEAKHURST%20NSW%202210%22%2C%22ErrorMessage%22%3Anull%7D%7D; agl-location=NSW',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'Cache-Control': 'max-age=0, no-cache',
        'Pragma': 'no-cache',
        'TE': 'Trailers'
    }
    data = "postCode="+postcode+"&customerType=Residential&fuelType=Electricity&tariffType=Unknown&energyPlan=All&isPowerdirectPage=False"
    r = requests.post(url, data=data, headers=headers)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        try:
            soup.find_all(id='noDataMsg')[0]
            return False
        except:
            pass
        rows = soup.find_all('tbody')[0].find_all('tr')
        urls = []
        for i in rows:
            atag = i.find_all('a')[0]
            urls.append(atag.get('href'))
        if urls:
            pool = ThreadPool(len(urls))
            results = pool.map(extractEnergyMadeEasy, urls)
            results = list(filter(bool, results))
            result = {}
            result['AGL'] = results
            queue.put(result)
            print(json.dumps(result, indent=4))
        else:
            print("no urls")
            return False
    else:
        print(r.reason, '\n', r.headers)
        return False

# when this function is called it uses a global postcode to get all electricity subplans for that postcode provided by the Energy Australia company
def getEnergyAustralia(queue):
    global postcode
    planNames = ['Total Plan', 'Basic Home', 'No Frills']
    urls = []
    for planName in planNames:
        url = 'https://www.energyaustralia.com.au/airpig-api/plan-documents?customerType=RES&postcode='+str(postcode)+'&offerName='+planName
        r = requests.get(url)
        if r.status_code == 200:
            for i in r.json()['searchResult']:
                urls.append(i['documentUrl'])
        else:
            return False
    if urls:
        pool = ThreadPool(len(urls))
        results = pool.map(extractEnergyMadeEasy, urls)
        result = {}
        result['EnergyAustralia'] = results
        queue.put(result)
    else:
        return False


# when this function is called it uses the global postcode to get all electricity subplans for that postcode provided by the Dodo company
def getDodo(queue):
    global postcode
    url = 'https://connectto.dodo.com/EnergySignup2015/PriceFactSheet/r/'+postcode
    r = requests.get(url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        cells = soup.find_all(class_='PfsDistributorContainerCellLink')
        urls = []
        for cell in cells:
            onclicklink = cell.get('onclick')
            if "showbasicplaninfo" in onclicklink.lower():
                planid = onclicklink.split("'")[1]
                url = 'https://www.energymadeeasy.gov.au/offer/'+planid[3:len(planid)-2]+"?stuff"
                urls.append(url)
        if urls:
            pool = ThreadPool(len(urls))
            results = pool.map(extractEnergyMadeEasy, urls)
            results = list(filter(bool, results))
            result = {}
            result['Dodo'] = results
            queue.put(result)
        else:
            return False
    else:
        return False

# this function takes an Energy Made Easy (energymadeeasy.gov.au) URL, scrapes all useful information within the page and returns that information in a JSON format to the calling function (the calling function 
# should be the plan's company's function e.g. if the plan is an Origin Energy plan, the calling function should be getOriginEnergy())
def extractEnergyMadeEasy(url):
    global postcode
    usplit = url.split('/')
    offernum = usplit[len(usplit)-1].split('?')[0]
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
    }
    url = 'https://www.energymadeeasy.gov.au/offer/'+offernum+'?postcode='+postcode
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        try:
            title = soup.find_all(class_='v2-title bp__summary-title')[0].contents[0]
            headline = soup.find_all(class_='headline__primary')[0].contents[0]
            if "gas" in title.lower() or "gas" in headline.lower():
                return False
            planID = soup.find_all(class_='plan-id')[0].contents[1].contents[0]
        except IndexError:
            return False
        features = []
        try:
            features_top = soup.find_all(class_='bp__summary-tariffs')[0].find_all(class_='icon__label')
            for i in features_top:
                feature = []
                for j in i.find_all('span')[0].contents:
                    if type(j) == bs4.element.Tag:
                        for k in j.contents:
                            feature.append(k)
                    else:
                        feature.append(j)
                feature = "".join(feature)
                features.append(feature)
        except:
            print("Error12")
        try:
            side_Bars = soup.find_all(class_='panel__item panel__item--raised')
            for i in side_Bars:
                if i.find_all('header')[0].contents[0] == 'Plan features':
                    aFeatures = i.find_all('li')
                    for j in aFeatures:
                        tag = j.find_all('span')[0]
                        while type(tag) == bs4.element.Tag:
                            tag = tag.contents[0]
                        features.append(tag)
        except:
            print("Error13")
        pricesurl = 'https://www.energymadeeasy.gov.au/offer/'+offernum+'/print?postcode='+postcode
        pricesr = requests.get(pricesurl)
        prices = []
        priceswodiscount = []
        pricesummary = {}
        usages = []
        tariff = []
        timeOfUseCharges = []
        if pricesr.status_code == 200:
            pricesoup = BeautifulSoup(pricesr.text, 'html.parser')
            try:
                pricerows = pricesoup.find_all(class_='bp__estimate-row')
                for i in pricerows:
                    price = i.find_all(class_='value')[0].contents[0]
                    usage = i.find_all(class_='data')[0].find_all('div')
                    discount = i.find_all(class_='discount')[0].find_all('strong')[0].contents[0]
                    for j in usage:
                        j = j.contents[0]
                        if not type(j) == bs4.element.Tag:
                            usage = j
                    usage = float(usage.split()[0])
                    price = float("".join(price.split(',')))
                    discount = float("".join(discount.split(',')))
                    priceswodiscount.append(discount)
                    prices.append(price)
                    usages.append(usage)
                    tariff.append({
                        'priceperkWh': price,
                        'usageperday': usage,
                        'priceWithOutDiscount': discount
                    })
            except:
                print("Error1")
            titles = []
            try:
                table = pricesoup.find_all(class_='panel__item panel__item--tabular topline')[0]
                titles = table.find_all(class_='panel__subnote')
                dataz = table.find_all('table')
                for i in range(len(titles)):
                    if len(titles[i]) == 5:
                        season = titles[i].contents[0].contents[0]
                        period = titles[i].contents[2].contents[0]
                        weekdays = titles[i].contents[4].contents[0]
                        tds = dataz[i].find_all('td')
                        name = None
                        startFrom = None
                        endAt = None
                        valueFor = None
                        typesymbol = 'cents/kWh'
                        details = []
                        for j in tds:
                            strongs = j.find_all('strong')
                            name = strongs[0].contents[0].split()
                            startFrom = name[1]
                            endAt = name[3]
                            name = name[0]
                            valueFor = float(strongs[1].contents[0].split()[0])
                            details.append({
                                'usageType': name,
                                'startFromHrs': startFrom,
                                'endAtHrs': endAt,
                                'price': valueFor,
                                'type': typesymbol
                            })
                        timeOfUseCharges.append({
                            'season': season,
                            'period': period,
                            'weekdays': weekdays,
                            'details': details
                        })
                pricesummary['timeOfUseCharges'] = timeOfUseCharges
            except:
                print(titles, offernum)
        else:
            print("Error has occured, HTTP%d" %(r.status_code))
            logfile = open("log.txt", 'w')
            print(r.text, file=logfile)
            return False
        panels = soup.find_all(class_='panel__item')
        feesandcharges = []
        discounts = None
        eligiblity = []
        solar = []
        greenpower = []
        additionalDetails = {}
        for i in panels:
            header = i.find_all('header')[0].contents
            if header[0] == 'Fees and charges':
                try:
                    li = i.find_all('li')
                    for j in li:
                        j = j.find_all('div')
                        if len(j) == 3:
                            titlea = j[0].contents[0]
                            description = j[1].contents[0]
                            amountstring = j[2].contents[0]
                            amount = None
                            typesymbol = None
                            if len(amountstring.split('$')) > 1:
                                amount = amountstring.split('$')[1]
                                typesymbol = '$'
                            elif len(amountstring.split('%')) > 1:
                                amount = amountstring.split('%')[0]
                                typesymbol = '%'
                            feeorcharge = {
                                'title': titlea,
                                'description': description,
                                'amount': float(amount),
                                'type': typesymbol
                            }
                            feesandcharges.append(feeorcharge)
                except:
                    print("Error2")
            elif header[0] == 'Price summary':
                try:
                    sections = i.find_all('section')
                    for j in sections:
                        titlec = j.find_all('header')[0]
                        if len(titlec.contents) == 1:
                            titlec = titlec.contents[0]
                        else:
                            titlec = titlec.find_all('span')[0].contents[0]
                        parts = j.find_all('p')
                        generalCharges = []
                        controlledLoad = []
                        multiple = False
                        if titlec == 'General charges' or titlec == 'Controlled load':
                            for k in parts:
                                kcontents = k.contents
                                chargename = "".join(kcontents[0].split(':')).strip()
                                value = None
                                minValue = None
                                maxValue = None
                                typesymbol = []
                                for m in range(len(kcontents)-1):
                                    m = m+1
                                    if type(kcontents[m]) == bs4.element.Tag:
                                        kcontents[m] = kcontents[m].contents[0]
                                        if ' to ' in kcontents[m]:
                                            multiple = True
                                            kcontents[m] = kcontents[m].split()
                                            minValue = float(kcontents[m][0])
                                            maxValue = float(kcontents[m][2])
                                            typesymbol.append(kcontents[m][3])
                                        else:
                                            multiple = False
                                            kcontents[m] = kcontents[m].split()
                                            value = float(kcontents[m][0])
                                            typesymbol.append(kcontents[m][1])
                                    else:
                                        typesymbol.append(kcontents[m])
                                typesymbol = "".join(typesymbol)
                                if titlec == 'General charges':
                                    if not multiple:
                                        generalCharges.append({
                                            'name': chargename,
                                            'value': value,
                                            'type': typesymbol
                                        })
                                    else:
                                        multiple = False
                                        generalCharges.append({
                                            'name': chargename,
                                            'minValue': minValue,
                                            'maxValue': maxValue,
                                            'type': typesymbol
                                        })
                                elif titlec == 'Controlled load':
                                    if not multiple:
                                        controlledLoad.append({
                                            'name': chargename,
                                            'value': value,
                                            'type': typesymbol
                                        })
                                    else:
                                        multiple = False
                                        controlledLoad.append({
                                            'name': chargename,
                                            'minValue': minValue,
                                            'maxValue': maxValue,
                                            'type': typesymbol
                                        })
                            if generalCharges:
                                pricesummary['generalCharges'] = generalCharges
                            if controlledLoad:
                                pricesummary['controlledLoad'] = controlledLoad
                except:
                    print("Error3")
            elif header[0] == 'Contract details':
                contractdetails = []
                titles = i.find_all('div')
                descriptions = i.find_all('p')
                for j in range(len(titles)):
                    desc = []
                    for k in descriptions[j]:
                        
                        if not type(k) == bs4.element.Tag:
                            desc.append(k.strip())
                        else:
                            while type(k) == bs4.element.Tag:
                                if len(k.contents) == 1:
                                    k = k.contents[0]
                                else:
                                    break
                            if not type(k) == bs4.element.Tag:
                                desc.append(k.strip())
                    desc = " ".join(desc)
                    contractdetails.append({
                        'title': titles[j].contents[0].contents[0],
                        'description': desc
                    })
                additionalDetails['contractDetails'] = contractdetails
            elif header[0] == 'Billing and price details':
                try:
                    billingdetails = []
                    titles = i.find_all('div')
                    descriptions = i.find_all('p')
                    options = i.find_all('li')
                    billingdetails.append({
                        'billingPeriod': descriptions[0].contents[0]
                    })
                    paymentOptions = []
                    for j in options:
                        paymentOptions.append(j.contents[0])
                    billingdetails.append({
                        'paymentOptions': paymentOptions
                    })
                    otherDetails = []
                    for j in range(len(descriptions)-1):
                        j = j + 1
                        if not "Enter your details from a recent bill to" in descriptions[j].contents[0]:
                            otherDetails.append(descriptions[j].contents[0])
                    billingdetails.append({
                        'otherDetails': otherDetails
                    })
                    additionalDetails['billingandPriceDetails'] = billingdetails
                except:
                    print("Error4")
            elif header[0] == 'Terms and conditions':
                try:
                    details = []
                    for j in i.find_all('p'):
                        details.append(j.contents[0])
                    additionalDetails['termsandConditions'] = {
                        'details': details
                    }
                except:
                    print("Error5")
            else:
                for j in header:
                    if "Discounts" in j:
                        try:
                            discountstemp = []
                            try:
                                secs = i.find_all(class_='hide-is-complex')
                                if len(secs) > 0:
                                    sections = secs[0].find_all('li')
                                else:
                                    sections = i.find_all('li')
                            except:
                                print("test", offernum)
                            for k in sections:
                                titleb = k.find_all(class_='panel__list-item')[0].contents[0]
                                description = k.find_all(class_='panel__list-subtext')[0]
                                if type(description) == bs4.element.Tag:
                                    description = description.contents[0]
                                value = k.find_all(class_='panel__list-value')[0].contents[0]
                                typesymbol = None
                                if len(value.split('%')) == 2:
                                    value = float(value.split('%')[0])
                                    typesymbol = '%'
                                discountstemp.append({
                                    'title': titleb,
                                    'description': description,
                                    'value': value,
                                    'type': typesymbol
                                })
                            try:
                                discounts = {
                                    'note': i.find_all(class_='panel__subnote')[0].contents[0],
                                    'discounts': discountstemp
                                }
                            except:
                                discounts = {
                                    'discounts': discountstemp
                                }
                        except:
                            print(k, offernum)
                    elif "Plan eligibility" in j:
                        try:
                            sections = i.find_all('li')
                            for k in sections:
                                titleb = k.find_all(class_='panel__list-item')[0].contents[0]
                                description = k.find_all(class_='panel__list-subtext')[0].contents[0]
                                eligiblity.append({
                                    'title': titleb,
                                    'description': description
                                })
                        except:
                            print("Error7")
                try:
                    for j in i.find_all('span'):
                        if "Solar feed-in" in j:
                            rows = i.find_all('tr')
                            for k in rows:
                                td = k.find_all('td')
                                description = td[0].contents[0]
                                value = None
                                typesymbol = None
                                for m in td[1].contents:
                                    if type(m) == bs4.element.Tag:
                                        value = float(m.contents[0])
                                    else:
                                        try:
                                            m.strip()
                                            typesymbol = m.strip()
                                        except:
                                            print("Error8")
                                solar.append({
                                    'description': description,
                                    'value': value,
                                    'type': typesymbol
                                })
                        elif "GreenPower" in j:
                            for k in i.find_all('tbody')[0].find_all('tr'):
                                td = k.find_all('td')
                                usage = td[0].contents[1].contents[0]
                                charge = td[1].contents[0].strip()
                                description = td[2].contents[0]
                                greenpower.append({
                                    'usage': usage,
                                    'charge': charge,
                                    'description': description
                                })
                except:
                    print("Error9")
        plan = {
            'title': title,
            'ID': planID,
            'features': features,
            'tariffs': tariff,
            'feesandCharges': feesandcharges,
            'discounts': discounts,
            'eligiblity': eligiblity,
            'priceSummary': pricesummary,
            'solar': solar,
            'greenpower': greenpower,
            'additionalDetails': additionalDetails
        }
        return plan
    else:
        return False

# this function runs 4 threads (one for each company function) to minimize the amount of time needed to retrieve the plans and retrieves and parses the output from the 4 functions into 1 coherent JSON object 
def getSubPlans(newPostcode=None):
    global postcode
    start = time.time()
    if newPostcode:
        postcode = str(newPostcode)
    if not checkPostcode():
        print("Need a valid postcode")
        return False
    que = queue.Queue()
    AGL = Thread(target=getAGL, args=[que])
    Dodo = Thread(target=getDodo, args=[que])
    EnergyAustralia = Thread(target=getEnergyAustralia, args=[que])
    OriginEnergy = Thread(target=getOriginEnergy, args=[que])
    AGL.start()
    Dodo.start()
    EnergyAustralia.start()
    OriginEnergy.start()
    AGL.join()
    Dodo.join()
    EnergyAustralia.join()
    OriginEnergy.join()
    companies = ['EnergyAustralia', 'AGL', 'Dodo', 'OriginEnergy']
    completeResults = {}
    results = []
    while not que.empty():
        results.append(que.get())
    for j in results:
        for i in companies:
            try:
                completeResults[i] = j[i]
            except KeyError:
                pass
    print("Executed in %.0f seconds" %(time.time()-start))
    return completeResults


# checks whether the postcode is a valid Australian postcode
def checkPostcode():
    global postcode
    try:
        cpostcode = postcode
        if type(postcode) == int:
            cpostcode = str(postcode)
        if len(cpostcode) == 4:
            intp = int(cpostcode)
            if intp >= 2000 and intp < 8000:
                return True
            elif intp >= 800 and intp < 1000:
                return True
            else:
                return False
        else:
            return False
    except ValueError:
        return False

# this, like the first part of the code is also a placeholder for testing and demonstration purposes
#runAll('2210')