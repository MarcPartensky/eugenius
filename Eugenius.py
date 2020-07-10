
class Error(Exception):  # TODO : mettre ça dans exceptions.py
    """Base class for exceptions in this module."""
    pass


class EugenieError(Error):
    pass


class OverkizError(Error):
    pass


import time
class Execution :
    def __init__(self, execId):
        self.execId=execId
        self.lastUpdateTime=int(time.time()*1000)#todo
    def update(self, dict_):
        self.state=dict_["newState"]
        self.lastUpdateTime=dict_['timestamp']

class State :
    def __init__(self, dict_):
        #types :
        #1 : int
        #2 : float
        #3 : str
        for key in dict_ :
            setattr(self, key, dict_[key])
    def set(self, dict_) :
        self.value=dict_['value']

    def update(self, dict_):
        self.value=dict_["value"]

class Device :
    def __init__(self, sdk, dict_):
        for key in dict_ :
            if key not in ["definition", "states"] :
                setattr(self, key, dict_[key])
        self.commands={cmd["commandName"]:cmd['nparams'] for cmd in dict_["definition"]["commands"]}
        self.states={s['qualifiedName']:State(s) for s in dict_['definition']['states']}
        self.overkiz=sdk

        for state in dict_['states'] :
            self.states[state['name']].set(state)


    def exec(self, cmd, *params):
        if cmd not in self.commands :
            raise OverkizError("{} is not a command of {} ({})".format(cmd, self.controllableName, self.label))

        if len(params)!=self.commands[cmd] :
            raise OverkizError("The command {} requires {} param(s), {} given".format(cmd, self.commands[cmd], len(params)))
        #todo check la valeur des params
        if params :
            return self.overkiz.exec(self.deviceURL, {"type": self.type, "name": cmd, "parameters":params})
        return self.overkiz.exec(self.deviceURL, {"type":self.type, "name":cmd})

    def update(self, dict_):
        if self.lastUpdateTime>dict_["timestamp"] :
            #the update is out-of-date
            logging.warning("The connection to the server is weird.")
            return

        self.lastUpdateTime=dict_["timestamp"]
        if dict_["name"]=="DeviceStateChangedEvent" :
            for stateUpdate in dict_["deviceStates"] :
                self.states[stateUpdate["name"]].update(stateUpdate)
        else :
            logging.warning("The event {} is not yet supported".format(dict_["name"]))

from collections import deque
class Home :
    def __init__(self, sdk, setupJson):
        self.overkiz=sdk
        self.setup=setupJson
        self.devices=[Device(sdk,device) for device in setupJson["devices"]]
        self.getDeviceByURL={d.deviceURL:d for d in self.devices}



from warrant.aws_srp import AWSSRP
import requests,json,logging
class Cognito:
    """Class to control """

    def __init__(self, username:str, password:str):
        self.username = username
        self.password = password
        self.poolRegion = "eu-west-1"
        self.poolID = 'eu-west-1_wj277ucoI'
        self.clientID = '3mca95jd5ase5lfde65rerovok'
        self.isConnected=False
        self.baseURL = "https://api.egn.prd.aws-nexity.fr/deploy/api/v1/"
        self.domoticState = None
        self.cognitoTokens = None

    def getTokens(self):
        """Authenticates with Cognito. Return Cognito's tokens as a dict.
        result format : {'AccessToken':'str','ExpiresIn':int,'IdToken':'str','RefreshToken':'str','TokenType':'str'}
        See : https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AuthenticationResultType.html"""
        self.aws = AWSSRP(username=self.username, password=self.password, pool_id=self.poolID,
                          pool_region=self.poolRegion,
                          client_id=self.clientID)#todo : manage authentification error
        self.cognitoTokens = self.aws.authenticate_user()['AuthenticationResult']
        self.isConnected=True
        return self.cognitoTokens

    def getDomoticToken(self):
        """Return the domotic token. The dotmotic token is required to connect to the Overkiz API"""
        if not self.isConnected :
            self.getTokens()
        headers = {
          'authorization': self.cognitoTokens['IdToken'],
          'accept': 'application/json',
          'content-type': 'application/json',
          'Accept-Encoding': 'gzip, deflate',
          'Host': 'api.egn.prd.aws-nexity.fr',
          'Connection': 'close',
          'User-Agent': 'okhttp/3.12.1'
        }

        response = requests.request("GET", self.baseURL+"users/current", headers=headers, data = {})
        self.info=json.loads(response.text)
        if 'message' in self.info:
            raise EugenieError(
                'Eugenie is unavailable : {}\nMake sure the application works.'.format(self.info['message']))
        #todo : "name":"Ventilation M\xc3\xa9canique Contr\xc3\xb4l\xc3\xa9e (VMC)"
        logging.info("Connected as {} {} {}".format(self.info["profile"]["civility"],self.info["profile"]["firstName"],self.info["profile"]["lastName"]))
        self.domoticState=self.info["profile"]["domoticState"]
        if (self.domoticState!="ACCEPTED") :
            logging.warning("Unkown expected problem with your domotic system : {}".format(self.domoticState))

        response = requests.request("GET", self.baseURL+"domotic/token", headers=headers, data={})

        self.domoticToken=json.loads(response.text)['token']

        try :
            postalCode=self.info['building']['address']['postalCode']
            response = requests.request("GET", self.baseURL + "buildings/weather/" + postalCode, headers=headers,
                                        data={})
            tmpJSON = json.loads(response.text)
            self.temperature = tmpJSON["temperature"]
            self.weatherCondition = tmpJSON['condition']
        except KeyError :
            logging.warning("Can't access data of your building")

        return self.domoticToken

import urllib, threading, sys
from json import JSONDecodeError
class Overkiz :
    def __init__(self,username, domoticToken):
        self.username=username
        self.domoticToken=domoticToken
        self.baseURL = "https://ha106-1.overkiz.com/enduser-mobile-web/enduserAPI/"
        self.jsessionid = None
        self.home=None
        self.keepAlive=False
        self.executions = deque([], maxlen=300)#todo : mettre ça dans des params
        self.eventIgnored = ["GatewaySynchronizationStartedEvent","GatewaySynchronizationEndedEvent"]
    def fecth(self):
        self.keepAlive = True
        while self.keepAlive:
            try:
                rep = self.request("POST", "events/{}/fetch".format(self.token))
                self.update(rep)
            except: # TODO refaire c moche
                e = sys.exc_info()[0]
                logging.error("Error dans le fetch {}".format(e))
                time.sleep(2)

    def disconnect(self):
        self.keepAlive=False
        self.thread.join()

    def update(self, array):
        tmpExec={execution.execId:execution for execution in self.executions}#todo : faire plus propre
        for element in array:
            if element["name"] in self.eventIgnored:
                continue

            if element['name']=="ExecutionStateChangedEvent" :
                if element['execId'] in tmpExec:
                    tmpExec[element['execId']].update(element)
                    continue
                else :
                    #logging.warning("Unexpected Execution information received")
                    newExecution=Execution(element['execId'])
                    newExecution.update(element)
                    self.executions.append(newExecution)
                    tmpExec = {execution.execId: execution for execution in self.executions}  # todo : faire plus propre

            if "deviceURL" in element:
                self.home.getDeviceByURL[element["deviceURL"]].update(element)
                continue

            logging.warning("{} is not supported yet".format(element['name']))


    def connect(self):
        """get "JSESSIONID" cookie to communicate with Overkiz API"""
        payload = "ssoToken={}&userId={}".format(urllib.parse.quote(self.domoticToken),
                                                 urllib.parse.quote(self.username))
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'ha106-1.overkiz.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'okhttp/3.12.1'
        }
        response = requests.request("POST", self.baseURL + "login", headers=headers, data=payload)
        if not (json.loads(response.text)["success"]):
            raise OverkizError("Unable to connect to Overkiz API : {}".format(response.text))
        #print(response.text)
        setCookie = response.headers['Set-Cookie']
        #setCookie's format : "JSESSIONID=5D0D507B906B631A1D4AE7970C5B12DC; Path=/enduser-mobile-web; Secure; HttpOnly"
        self.jsessionid = setCookie[11:].split(";")[0]
        self.headers = {
            'content-type': 'application/json',
            'Host': 'ha106-1.overkiz.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate',
            'Cookie': 'JSESSIONID={}'.format(self.jsessionid),
            'User-Agent': 'okhttp/3.12.1'
        }

    def getHome(self):
        """Return a Home instance"""
        if not(self.jsessionid) :#check if we are not connected
            self.connect()
        if self.home :
            return self.home
        self.domoticInfo = self.request("GET", "setup")
        self.home=Home(self, self.domoticInfo)
        self.domoticInfoPlaces = self.request("GET","setup/places" )
        #skip : setup/devices/states/refresh, exec/current,
        self.token=self.request("POST","events/register")["id"]#used
        self.thread = threading.Thread(target=self.fecth, args=())
        self.thread.start()
        return self.home

    def request(self,method, url, data={}):
        """Makes a request to Overkiz API"""
        response = requests.request(method, self.baseURL + url, headers=self.headers, data=data)
        #print(self.headers)
        try :
            repJSON = json.loads(response.text)
            if ("errorCode" in repJSON) :
                raise OverkizError("{} : {}".format(repJSON["errorCode"], repJSON["error"]))
            else:
                return repJSON

        except JSONDecodeError :
            raise OverkizError("Unexpected response from Overkiz API url={} method={}\nreponse.text={}".format(url, method, response.text))

    def exec(self, deviceURL, *dictcmd):
        """Ask the device at the adress deviceURL to excute commands"""
        data={"actions":[{"deviceURL":deviceURL, "commands":dictcmd}]}
        payload = json.dumps(data)
        logging.info("sending command : {}".format(payload))
        #rep = requests.request("POST", self.baseURL + "exec/apply", headers=self.headers, data=payload)
        rep = self.request("POST", "exec/apply", data=payload)
        print(rep)
        newExecution=Execution(rep["execId"])
        self.executions.append(newExecution)
        return newExecution

    def execMany(self, array):
        #element array de la forme : deviceURL, *dictcmd
        data={"actions":[{"deviceURL":element[0], "commands":element[1:]} for element in array]}
        payload = json.dumps(data)
        print("la cmd envoyé : {}".format(payload))
        rep = self.request("POST", "exec/apply", data=payload)
        newExecution = Execution(rep["execId"])
        self.executions.append(newExecution)
        return newExecution


class Eugenius:
    """class for users"""

    def __init__(self, mailAdress: str, password: str):
        self.username = mailAdress.replace("@", "_-_")
        self.password = password
        self.overkiz = None

    def connect(self):
        """Connect to https API"""
        self.cognito=Cognito(self.username, self.password)
        domoticToken=self.cognito.getDomoticToken()
        self.overkiz=Overkiz(self.username,domoticToken)

    def disconnect(self):
        self.overkiz.disconnect()

    def getHome(self):
        if not(self.overkiz) :
            self.connect()
        return self.overkiz.getHome()

