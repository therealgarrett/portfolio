from pyzillow.pyzillow import ZillowWrapper
from pyzillow.pyzillow import GetUpdatedPropertyDetails
from pyzillow.pyzillow import GetDeepSearchResults
from uszipcode import SearchEngine
from uszipcode import SearchEngine
from pprint import pprint
from bs4 import BeautifulSoup
from termcolor import colored
import sys
import requests
import argparse
import inquirer
import pymysql as db
import re


def request(zipcode, sort):
    """
    This function returns values from Zillow html docs and then parses.
    """

    # user agents required for access
    req_headers = {
        'accept': 'text/html,application/xhtml+xml,application/\
            xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/\
            537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }
    cnxt = db.connect(user="root", password="u0bj8dsvs1n",
                      host="localhost",
                      database="sys",
                      charset="utf8mb4")
    # lost and found  - 'X1-ZWz1fjckjdd8gb_a2eph'
    # Init api with Zillow access key
    API = ZillowWrapper('X1-ZWz186lbvmr8cr_517ck')
    cursor = cnxt.cursor()
    content = []
    # init url's
    with requests.Session() as s:
        try:
            if sort == "newest":
                url = "https://www.zillow.com/homes/for_sale/\
                    {0}/days_sort".format(zipcode)
            elif sort == "cheapest":
                url = "https://www.zillow.com/homes/for_sale/\
                    {0}/pricea_sort/".format(zipcode)
            url = url.strip()
            print(url)
            r = s.get(url, headers=req_headers, timeout=5)
            soup = BeautifulSoup(r.content, 'lxml')
            # get max page number
            max = 0
            for i in soup.find_all("a"):
                if i.get('onclick') is not None:
                    try:
                        if i.get('onclick'):
                            if(re.findall('\d+', i.get('onclick'))):
                                for j in re.findall('\d+', i.get('onclick')):
                                    if max < int(j):
                                        max = int(j)
                    except IndexError:
                        pass
            hold = url
            print(colored("Examining Zillow ..", 'green'))
            for i in range(1, max):
                if sort == "newest":
                    url = url + "/" + str(i) + "_p/"
                else:
                    url = url + str(i) + "_p/"
                r = s.get(url, headers=req_headers, timeout=5)
                soup = BeautifulSoup(r.content, 'lxml')
                if sort == "cheapest":
                    address_ref = [i.text for i in soup.find_all(
                        'span', {'itemprop': 'address'})]
                    prices = [i.text for i in soup.find_all(
                        'span', {'class': 'zsg-lg-1-4 zsg-right-aligned'})]
                    try:
                        for j in range(len(address_ref)):
                            if address_ref[j][0].isdigit() is True:
                                a = address_ref[j].split()
                                z = a[-1]
                                a.remove(a[-1])
                                a = " ".join(a)
                                print(a)
                                # Zillow wrapper fails with hashmarks
                                if "#" not in a:
                                    response = API.get_deep_search_results(a, z)
                                    result = GetDeepSearchResults(response)
                                    if result.zestimate_amount is not None:
                                        amount = int(result.zestimate_amount)
                                        try:
                                            prices[j] = "$" + str(format(amount, ','))
                                        except IndexError:
                                            prices.insert(j, "$" + str(format(amount, ',')))

                                    else:
                                        continue
                            else:
                                continue
                    except BaseException as e:
                        print("API error: %s" % str(e))
                        print("Defaulting to BeautifulSoup")
                        prices = [i.text for i in soup.find_all(
                            'span', {'class': 'zsg-lg-1-4 zsg-right-aligned'})]
                        break

                else:
                    prices = [i.text for i in soup.find_all(
                        'span', {'class': 'zsg-photo-card-price'})]

                info = [i.text for i in soup.find_all(
                    'span', {'class': 'zsg-photo-card-info'})]
                address = [i.text for i in soup.find_all(
                    'span', {'itemprop': 'address'})]
                # creates nested list of Zillow listing
                for j, r in enumerate(prices):
                    content.extend([[prices[j], info[j], address[j]]])
                    Price = prices[j]
                    Info = info[j]
                    Address = address[j]
                    query = "INSERT INTO PySpider (Price, Info,\
                        Address) VALUES (%s,%s,%s)"
                    cursor.execute(
                        query,
                        (Price, Info, Address))
                    cnxt.commit()
                url = hold
            print(colored('\n' + "Listings: " + str(len(content)), "green"))

        except BaseException as e:
            print("An error has occured: %s") % str(e)




def truncate():
    cnxt = db.connect(user="root", password="u0bj8dsvs1n",
                      host="localhost",
                      database="sys",
                      charset="utf8mb4")
    cursor = cnxt.cursor()
    ask = input("Reset PySpider? [yn]")
    if ask == "y" or ask == "Y":
        try:
            cursor = cnxt.cursor()
            delete = "truncate PySpider"
            cursor.execute(delete)
            remainder = cursor.execute("SELECT * FROM PySpider ")
            print(colored("Remaining rows: " + str(remainder), "green"))
        except BaseException as e:
            print(colored("Error on_data: %s", "red") % str(e))
    elif ask == "n" or ask == "N":
        main()


def search():
    """
    This function takes city and state as an input, and returns
    the string value. Search() also will automatically execute
    the same logic found in lookup().
    """

    code = input("Enter [city,state]: ").split(',')
    a = SearchEngine(simple_zipcode=True)
    zipcode = a.by_city_and_state(code[0], code[1])[0]
    print(colored("Zipcode Information:", "green"))
    pprint(zipcode.to_json())
    target = " ".join(code)
    return target

def deep_search():
    return

def lookup():
    """
    Lookup() returns zipcode information.
    """

    b = input("Enter [zipcode]: ")
    # Allows the user to pull simple or complex zipcode information
    while True:
        d = input("Simple or complex? [s/c]")
        if d == 's' or d == 'S':
            f = SearchEngine(simple_zipcode=True)
            break
        elif d == 'c' or d == 'C':
            f = SearchEngine(simple_zipcode=False)
            break
        else:
            print(colored("Incorrect input.", "red"))
            print("Try 's' or 'c'")
    zipcode = f.by_zipcode(b)
    pprint(zipcode.to_json())


def main():
    """
    Main() calls the main menu.
    """

    inquire = [
        inquirer.List("Listings",
                      message="Which option do you need?",
                      choices=["Newest", "Cheapest",
                               "Zipcode Info", "Truncate", "Quit"],
                      ),
    ]
    inquire = inquirer.prompt(inquire)
    if inquire["Listings"] == "Newest":
        newzip = search()
        filtered = "newest"
        request(newzip, filtered)
        main()
    elif inquire["Listings"] == "Cheapest":
        cheapzip = search()
        filtered = "cheapest"
        request(cheapzip, filtered)
        main()
    elif inquire["Listings"] == "Zipcode Info":
        lookup()
        main()
    elif inquire["Listings"] == "Truncate":
        truncate()
        main()
    elif inquire["Listings"] == "Quit":
        sys.exit()


if __name__ == "__main__":
    main()
