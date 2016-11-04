#!/usr/bin/python

from requests import session 
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from uuid import uuid4 as uuid

email = ""
password = ""
#set this if you run the script from commandline
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
            "rememberMe": "on",
            "_rememberMe": "on",
            "gCaptchaResponse": "",
            "_eventId": "submit",
            "password": password,
            "email": email}
    _retries = Retry(
            total=4,
            backoff_factor=3,
            status_forcelist=[ 104, 500, 502, 504 ])
            

    def __init__(self):
        self._s = session()
        self.a = HTTPAdapter(max_retries=self._retries)
        self._s.mount("https://", self.a)
        self.loginea()
        self.loginapi()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.logoutapi()

    def loginea(self):
        """
        Here we redirect from the companion page to get the login page. This
        returns us back to the companion on a successful login.
        TODO: 
        Check cookie or request URL? 
        """
        if not self._authenticated:
            r = self._s.get(self._login, timeout=self._timeout)
            r.raise_for_status()
            r = self._s.post(r.url, data=self._formdata, timeout=self._timeout)
            r.raise_for_status()
            if "ealocale" in r.cookies:
                self._authenticated = True
            else:
                raise Exception("Failed to log into your EA account.")

    def getauthcode(self):
        """
        This retrieves a random code used to start a session with the API
        """
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
        """
        This starts a session with the API backend
        """
        authcode = self.getauthcode()
        params = {
                "code": authcode,
                "redirectUri": "nucleus:rest"
                }
        r = self.jsonRPC("Companion.loginFromAuthCode", params)
        self._sessionID = r["id"]

    def logoutapi(self):
        """ 
        Unsure if this is necessary at all but given this isn't an officially
        public API lets be nice and not leave open sessions for single cmdline
        calls.
        """
        r = self.jsonRPC("Companion.logout")
        self._session = ""
    
    def keepalive(self):
        """
        The website does this every 5 minutes.
        TODO:
        Use until an idle timer reached then logout?
        """
        r = self._s.get("https://www.battlefield.com/service/keep-alive.json")
        r.raise_for_status()

    def jsonRPC(self, method, params={}):
        """
        Formats and sends the json data to the API and returns the response
        """
        headers = {"Content-Type": "application/json"}
        if self._sessionID:
            headers["X-GatewaySession"] = self._sessionID
        json = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": str(uuid())
                }
        r = self._s.post(self._api, params=method, json=json, headers=headers,
                         timeout=self._timeout)
        result = r.json()
        if "error" in result:
            error = result["error"]["message"]
            print("ERROR:\n{}\nATTEMPT FAILED:\nmethod:{}\njson:{}\n"
                  "headers:{}\n".format(error, method, json, headers))
        elif "result" in result:
            return result["result"]
        else:
            raise Exception("Unknown JSON data returned: {}".format(json))
            return
    
    def getinitdata(self):
        """
        This gets your own data, personas, ids, etc
        """
        params = {"locale": "en-US"}
        r = self.jsonRPC("Companion.initApp")
        return r

    def getapistatus(self):
        """
        Queries for login status.
        """
        r = self.jsonRPC("Companion.isLoggedIn")
        return r

    def getcareerstats(self, personaid):
        """
        Combined BF4 + BF1 career stats. BF:H at some point too probably
        Mostly just highlights, top weapon, rank, etc 
        """
        params = {"personaId": personaid}
        r = self.jsonRPC("Stats.getCareerForOwnedGamesByPersonaId",
                              params=params)
        return r

    def getfriendslist(self):
        """
        Entire friends list is returned. You can find their personaId here
        """
        r = self.jsonRPC("Friend.getFriendsWithPresence")
        return r

    def getemblem(self, personaid):
        """
        Returns URL to emblem if it exists, otherwise null
        """
        params = {"personaId": personaid}
        r = self.jsonRPC("Emblems.getEquippedEmblem", params=params)
        return r

    def getweaponsstats(self, game, personaid):
        """
        Returns all weapons stats, kills, hs, etc
        """
        params = {
                "game": game,
                "personaId": personaid
                }
        r = self.jsonRPC("Progression.getWeaponsByPersonaId",
                              params=params)
        return r

    def getweapon(self, game, guid, personaid):
        """
        Returns data about a specific weapon
        """
        params = {
                "game": game,
                "guid": guid,
                "personaId": personaid
                }
        r = self.jsonRPC("Progression.getWeapon", params=params)
        return r

    def getvehiclesstats(self, game, personaid):
        """
        Returns all vehicle stats, kills, time, destroyed, etc
        """
        params = {
                "game": game,
                "personaId": personaid
                }
        r = self.jsonRPC("Progression.getVehiclesByPersonaId",
                              params=params)
        return r

    def getvehicle(self, game, guid, personaid):
        """
        Returns data about a specific vehicle
        """
        params = {
                "game": game,
                "guid": guid,
                "personaId": personaid
                }
        r = self.jsonRPC("Progression.getVehicle", params=params)
        return r

    def getdetailedstats(self, game, personaid):
        """
        Returns more detailed player stats rather than just highlights
        """
        params = {
                "game": game,
                "personaId": personaid
                }
        r = self.jsonRPC("Stats.detailedStatsByPersonaId", params=params)
        return r


if __name__ == "__main__":
    bf = BFCompanion()
    stats = bf.getcareerstats(personaId)
    print(stats)
