import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from swap import SwapMethod
from creds import KrakenCreds
from notify import Logger

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pyotp
from selenium.webdriver.common.action_chains import ActionChains
from tkinter import Tk

COIN_SATS = 100_000_000
MIN_LN_DEPOSIT = 1000
MAX_LN_DEPOSIT = COIN_SATS


class Kraken(SwapMethod):
    def __init__(self, creds: KrakenCreds, log: Logger):
        self.log = log
        self.api_url = "https://api.kraken.com/"
        self.creds = creds
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"kraken deposit address: {addr}",
            "send_onchain": lambda sats: f"kraken initiated {sats} sat widthdrawl",
            "get_onchain_fee": lambda fee, sats: f"kraken fee: {fee} sats widthdraw amount: {sats} sats",
            "get_pending_send_sats": lambda status, ref, amt: f"kraken [{status}] widthdraw #{ref} of {amt} sats",
            "get_account_balance": lambda sats: f"kraken account balance: {sats} sats",
            "send_to_acct": lambda sats: f"Hey boss, {int(sats)} sats ready for kraken deposit"
        }

    @staticmethod
    def get_kraken_signature(urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def check_errors(self, response, payload, endpoint):
        if response['error']:
            for err in response['error']:
                err_msg = f"kraken responded with error: {err}"
                self.log.error(err_msg)
                self.log.notify(err_msg)
            self.log.error('using payload: {}'.format(payload))
            self.log.error('from : {}'.format(endpoint))
            sys.exit()

    def kraken_request(self, uri_path, data):
        headers = {}
        headers['API-Key'] = self.creds.api_key
        headers['API-Sign'] = self.get_kraken_signature(
            uri_path,
            data,
            self.creds.api_secret
        )
        req = requests.post(
            (self.api_url + uri_path),
            headers=headers,
            data=data
        ).json()
        self.check_errors(req, data, uri_path)
        return req['result']

    def get_onchain_address(self):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "method": "Bitcoin",
        }
        res = self.kraken_request('/0/private/DepositAddresses', payload)
        addr = res[0]['address']
        self.log.info(self.log_msg_map['get_onchain_address'](addr))
        return addr

    def send_onchain(self, sats, fee):
        # kraken does not use variable fee
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/Withdraw', payload)
        self.log.info(self.log_msg_map['send_onchain'](sats))
        return res

    def estimate_onchain_fee(self, sats):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT",
            "key": self.creds.funding_key,
            "amount": sats / COIN_SATS
        }
        res = self.kraken_request('/0/private/WithdrawInfo', payload)
        fee_quote = {
            'amount': int(float(res['amount']) * COIN_SATS),
            'fee': int(float(res['fee']) * COIN_SATS)
        }
        self.log.info(self.log_msg_map['get_onchain_address'](fee_quote['fee'], sats))
        return fee_quote['fee']

    def get_pending_send_sats(self):
        sends = self.get_recent_sends()
        pending_amt = 0
        for w in sends:
            if w['status'] in ['Initial', 'Pending']:
                pending_amt += int(float(w['amount']) * COIN_SATS)
                self.log.info(self.log_msg_map['get_pending_send_sats'](w['status'].lower(), w['refid'], w['amount']))
        return pending_amt

    def get_recent_sends(self):
        payload = {
            "nonce": str(int(1000 * time.time())),
            "asset": "XBT"
        }
        res = self.kraken_request('/0/private/WithdrawStatus', payload)
        return res

    def get_account_balance(self):
        payload = {"nonce": str(int(1000 * time.time()))}
        res = self.kraken_request('/0/private/Balance', payload)
        balance = int(float(res['XXBT']) * COIN_SATS)
        self.log.info(self.log_msg_map['get_account_balance'](balance))
        return balance

    def send_to_acct(self, sats, node):
        self.log.notify(self.log_msg_map['send_to_acct'](int(sats)))

    def pay_invoice(self, invoice_code):
        # TODO kraken hasn't implemented yet
        return

    def get_lightning_invoice(self, amount_sats):
        chrome_options = Options()
        chrome_options.headless = True
        chrome_options.add_argument("user-data-dir=selenium") # create cookies to use next time
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path="./chromedriver")
        actions = ActionChains(driver)

        # go to invoice page, login if necessary, you may have to approve a new device the first time as well
        driver.get("https://www.kraken.com/u/funding/deposit?asset=BTC&method=1")
        time.sleep(1)
        location = driver.current_url
        if location != "https://www.kraken.com/u/funding/deposit?asset=BTC&method=1":
            if location == "https://www.kraken.com/sign-in":
                driver.find_element(By.XPATH, '//input[@name="username"]').send_keys(self.creds.username)
                driver.find_element(By.XPATH, '//input[@name="password"]').send_keys(self.creds.password)
                time.sleep(1)
                driver.find_element(By.XPATH, '//input[@name="password"]').send_keys(Keys.RETURN)
                time.sleep(2)
                if self.creds.otp_secret:
                    hotp = pyotp.TOTP(self.creds.otp_secret)
                    otp = hotp.now()
                    driver.find_element(By.XPATH, '//input[@name="tfa"]').send_keys(otp)
                    time.sleep(1)
                    driver.find_element(By.XPATH, '//input[@name="tfa"]').send_keys(Keys.RETURN)
                    time.sleep(3)
                driver.get("https://www.kraken.com/u/funding/deposit?asset=BTC&method=1")
                time.sleep(3)
                location = driver.current_url
        assert location == "https://www.kraken.com/u/funding/deposit?asset=BTC&method=1"
        time.sleep(1)

        # make everything on the page visible
        driver.execute_script("document.body.style.zoom = '0.55'")

        # remove tos popup
        driver.execute_script(
            "return document.getElementsByClassName('Dialog_dialog__f48Ay body-1 relative tos-dialog-lightning_dialog__hrFat')[0].parentElement.parentElement.parentElement.parentElement.remove();"
            #     "return document.getElementsByClassName('Button_button__caA8R Button_primary__c5lrD Button_large__T4YrY no-tab-highlight')[0].click();"
        )
        time.sleep(1)

        # toggle sats denomination if necessary
        sats_toggle = driver.find_element(By.CLASS_NAME, 'LightningForm_toggle__ZQNS6')
        if sats_toggle.get_attribute("class") == "LightningForm_toggle__ZQNS6 LightningForm_enabled__uWiT2":
            pass
        else:
            sats_toggle.click()

        # enter payment amount
        amt_field = driver.find_element(By.XPATH, '//*[@id="lightningDepositAmount"]')
        amt_field.send_keys(str(amount_sats))
        time.sleep(1)

        # focus submit button and press enter
        driver.execute_script(
            "document.getElementsByClassName('Button_button__caA8R Button_primary__c5lrD Button_large__T4YrY mt3 no-tab-highlight')[0].focus();")
        actions = actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(1)

        # copy lightning invoice to clipboard
        driver.execute_script(
            "document.getElementsByClassName('flex IconButton_button__g2fhQ caption-4 text-P500 mr1 no-tab-highlight')[0].click();")
        invoice_str = Tk().clipboard_get()
        return invoice_str
