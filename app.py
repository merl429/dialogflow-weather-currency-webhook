# -*- coding:utf8 -*-
# !/usr/bin/env python
# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    # print("Request:")
    # print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    if req.get("result").get("action") == "yahooWeatherForecast":
        baseurl = "https://query.yahooapis.com/v1/public/yql?"
        yql_query = makeYqlQuery(req)
        if yql_query is None:
            return {}
        yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
        result = urlopen(yql_url).read()
        data = json.loads(result)
        res = makeWebhookResult(data)
        return res
    elif req.get("result").get("action") == "currencyConverter":
        usdUrl = "http://spreadsheets.google.com/feeds/list/0Av2v4lMxiJ1AdE9laEZJdzhmMzdmcW90VWNfUTYtM2c/2/public/basic?alt=json"
        eurUrl = "http://spreadsheets.google.com/feeds/list/0Av2v4lMxiJ1AdE9laEZJdzhmMzdmcW90VWNfUTYtM2c/1/public/basic?alt=json"
        gbpUrl = "http://spreadsheets.google.com/feeds/list/0Av2v4lMxiJ1AdE9laEZJdzhmMzdmcW90VWNfUTYtM2c/5/public/basic?alt=json"
        usdData = json.loads(urlopen(usdUrl).read())
        eurData = json.loads(urlopen(eurUrl).read())
        gbpData = json.loads(urlopen(gbpUrl).read())
        
        forexData = combineForexData(usdData,eurData,gbpData)
        
        toCurrency = req.get("result").get("parameters").get("Currency").upper()
        unitCurrency = req.get("result").get("parameters").get("unit-currency")
        firstUnitCurrency = unitCurrency[0]
        fromCurrency = firstUnitCurrency.get("currency").upper()
        amount = firstUnitCurrency.get("amount")
        res = getCurrency(forexData,amount,fromCurrency,toCurrency)
        return res
    else:
        return {}
    
def testForex(usdData):
    speech = "Testing forex"
    try:
        for x in usdData['feed']['entry']:
            key = 'USD-'+x['title']['$t']
            factorData = x['content']['$t']
            factorA,factorB = factorData.split(" ")
            speech = key
            break
    except:
        speech = "error"
    return {
        "speech": speech,
        "displayText": speech,
        "data": {},
        "contextOut": [],
        "source": "Google Forex"
    }


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"


def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today the weather in " + location.get('city') + ": " + condition.get('text') + \
             ", And the temperature is " + condition.get('temp') + " " + units.get('temperature')

    # print("Response:")
    # print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        "data": {},
        "contextOut": [],
        "source": "Yahoo Weather"
    }
    
def combineForexData(usdData,eurData,gbpData):
    forex = {}
    for x in usdData['feed']['entry']:
        key = 'USD-'+x['title']['$t']
        factorData = x['content']['$t']
        factorA,factorB = factorData.split(" ")
        forex[key] = factorB
    for y in eurData['feed']['entry']:
        key = 'EUR-'+y['title']['$t']
        factorData = y['content']['$t']
        factorA,factorB = factorData.split(" ")
        forex[key] = factorB
    for z in gbpData['feed']['entry']:
        key = 'GBP-'+z['title']['$t']
        factorData = z['content']['$t']
        factorA,factorB = factorData.split(" ")
        forex[key] = factorB
    return forex
    
def getCurrency(forex,amount,fromCurrency,toCurrency):
    speech = "Testing currency: " + str(amount) + " " + fromCurrency + " " + toCurrency
    try:
        key = fromCurrency+"-"+toCurrency
        speech = forex.get(key)
    except:
        speech = "error"
    return {
        "speech": speech,
        "displayText": speech,
        "data": {},
        "contextOut": [],
        "source": "Google Forex"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
