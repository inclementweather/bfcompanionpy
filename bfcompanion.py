#!/usr/bin/python

from requests import session as session
from uuid import uuid4 as uuid

email = ""
password = ""
# you can find this number in the url after logging into battlefield companion
personaId = ""

class BFCompanion():
    _timeout = 20 
    _sessionID = ""
    _authenticated = False
    _login = "https://www.battlefield.com/login?postAuthUri=/companion" 
    _api = "https://companion-api.battlefield.com/jsonrpc/web/api"
    _nucleus = "https://accounts.ea.com/connect/auth?client_id=" \
               "sparta-companion-web&response_type=code&prompt=none" \
               "&redirect_uri=nucleus:rest"
    _formdata = {
            "rememberMe" : "on", 
            "_rememberMe" : "on", 
            "gCaptchaResponse" : "", 
            "_eventId" : "submit", 
            "password" : password,
            "email" : email
            }

    def __init__(self):
        self._s = session()
        self.loginea()
        self.loginapi()

    def loginea(self):
        if self._authenticated == False:
            # using companion redirect
            r = self._s.get(self._login)
            r.raise_for_status()
            # login to ea and check for cookie
            r = self._s.post(r.url, data=self._formdata)
            r.raise_for_status()
            if r.cookies["ealocale"]:
                self._authenticated = True
            else:
                raise Exception("Failed to log into your EA account.")
        return

    def getauthcode(self):
        r = self._s.get(self._nucleus)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            self.loginea()
            r = self._s.get(self._nucleus)
            r.raise_for_status()
            data = r.json()
        elif "code" in data:
            return data["code"]
        else:
            raise Exception("Unable to retrieve auth code from nucleus host.")

    def loginapi(self):
        authcode = self.getauthcode()
        params = {
                "code" : authcode,
                "redirectUri" : "nucleus:rest"
                }
        result = self.jsonRPC("Companion.loginFromAuthCode", params)
        self._sessionID = result["id"]
    
    def checkapi(self):
        response = self.jsonRPC("Companion.isLoggedIn")
        return response["isLoggedIn"]
        
    def jsonRPC(self, method, params={}):
        # implement some kind of backoff or use async?
        headers = { "Content-Type" : "application/json" }
        if self._sessionID:
            headers["X-GatewaySession"] = self._sessionID 
        json = {
                "jsonrpc" : "2.0",
                "method" : method,
                "params" : params,
                "id" : str(uuid())
                }
        r = self._s.post(self._api, params=method, json=json, headers=headers,\
                        timeout=self._timeout)
        r.raise_for_status()
        result = r.json()["result"]
        return result 
    
    def getcareerstats(self, personaid):
        params = { "personaId" : personaid }
        result = self.jsonRPC("Stats.getCareerForOwnedGamesByPersonaId",\
                             params=params)
        return result


if __name__ == "__main__":
    bf = BFCompanion();
    stats = bf.getcareerstats(personaId)
    print(stats)