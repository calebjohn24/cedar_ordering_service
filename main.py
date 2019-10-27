import datetime
import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import pygsheets
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
import pytz
from flask import Flask, request, session
from flask import redirect, url_for
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict

infoFile = open("info.json")
info = json.load(infoFile)
uid = info['uid']
#gc = pygsheets.authorize(service_file='static/CedarChatbot-70ec2d781527.json')
email = "cedarchatbot@appspot.gserviceaccount.com"
estName = info['uid']
estNameStr = info['name']
botNumber = info["number"]
gsheetsLink = info["gsheets"]
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/'
})
sqRef = db.reference(str('/restaurants/' + estNameStr))
print(sqRef.get())
squareToken = sqRef.get()["sq-token"]
promoPass = "promo-" + str(estName)
addPass = "add-" + str(estName)
remPass = "remove-" + str(estName)
#sh = gc.open('TestRaunt')
webLink = "sms:+" + botNumber + "?body=order"
sender = 'receipts@cedarrobots.com'
emailPass = "Cedar2421!"
smtpObj = smtplib.SMTP_SSL("smtp.zoho.com", 465)
smtpObj.login(sender, emailPass)
squareClient = Client(
    access_token=squareToken,
    environment='production',
)
dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}
app = Flask(__name__)
sslify = SSLify(app)
scKey = uuid.uuid4()
app.secret_key = scKey

api_locations = squareClient.locations
mobile_authorization_api = squareClient.mobile_authorization
result = api_locations.list_locations()
locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########
def getSquare():
    if result.is_success():
        # The body property is a list of locations
        locations = result.body['locations']
        # Iterate over the list
        for location in locations:
            if ((dict(location.items())["status"]) == "ACTIVE"):
                # print((dict(location.items())))
                addrNumber = ""
                street = ""
                for ltrAddr in range(len(dict(location.items())["address"]['address_line_1'])):
                    currentLtr = dict(location.items())["address"]['address_line_1'][ltrAddr]
                    try:
                        int(currentLtr)
                        addrNumber += currentLtr
                    except Exception as e:
                        street = dict(location.items())["address"]['address_line_1'][
                                 ltrAddr + 1:len(dict(location.items())["address"]['address_line_1'])]
                        break

                addrP = str(addrNumber + "," + street + "," + dict(location.items())["address"]['locality'] + "," +
                            dict(location.items())["address"]['administrative_district_level_1'] + "," +
                            dict(location.items())["address"]['postal_code'][:5])
                timez = dict(location.items())["timezone"]
                tz = pytz.timezone(timez)
                tzGl.append(pytz.timezone(timez))
                locationName = (dict(location.items())["name"]).replace(" ", "-")
                locationId = dict(location.items())["id"]
                numb = dict(location.items())['phone_number']
                numb = numb.replace("-", "")
                numb = numb.replace(" ", "")
                numb = numb.replace("+", "")
                locationsPaths.update(
                    {locationName: {
                        "id": locationId, "OCtimes": dict(location.items())["business_hours"]["periods"],
                        "sqEmail": dict(location.items())['business_email'],
                        "sqNumber": numb, "name": locationName}})


def checkLocation(location, custFlag):
    try:
        locationsPaths[location]
        return [0,0]
    except Exception as e:
        if (custFlag == 0):
            return [1, "pickLocation"]
        elif (custFlag == 1):
            return [1, "MobileStart"]
        elif (custFlag == 1):
            return [1, "EmployeeLocation"]


def checkAdminToken(idToken, username):
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if ((idToken == user_ref["token"]) and (time.time() - user_ref["time"] < adminSessTime)):
        return 0
    else:
        return 1





@app.route('/admin', methods=["GET"])
def login():
    return render_template("POS/Admin/login.html", btn=str("admin2"), restName=estNameStr)

@app.route('/forgot-password', methods=["GET"])
def pwReset():
    return render_template("POS/Admin/forgot-password.html", btn=str("admin2"), restName=estNameStr)



@app.route('/admin2', methods=["POST"])
def loginPageCheck():
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    email = str(rsp["emailAddr"])
    pw = str(rsp["pw"])
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    email = str(email).replace(".","-")
    try:
        user = ref.get()[str(email)]
        if ((pbkdf2_sha256.verify(pw, user["password"])) == True):
            print("found")
            LoginToken = str((uuid.uuid4())) + "-" + str((uuid.uuid4()))
            user_ref = ref.child(str(email))
            user_ref.update({
                'token': LoginToken,
                'time': time.time()
            })
            session['user'] = email
            session['token'] = LoginToken
            return redirect(url_for('panel'))
        else:
            print("incorrect password")
            return render_template("login2.html", btn=str("admin2"), restName=estNameStr)
    except Exception as e:
        print(e)
        return render_template("POS/Admin/login2.html", btn=str("admin2"), restName=estNameStr)


@app.route('/admin-panel', methods=["GET"])
def panel():
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.get()[str(username)]
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    getSquare()
    LocName = list(locationsPaths.keys())
    return render_template("POS/Admin/AdminPanel.html",
                           restName=estNameStr,
                           LocName=LocName,
                           lenLocName=len(LocName))



@app.route('/admin-location/<location>')
def locPanel(location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    doc = ref.get()[str(username)]
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login', location=location))
    print(checkLocation(location,1))
    if(checkLocation(location,1)[0] == 1):
        return redirect(url_for('.login', location=location))
    getSquare()
    LocName = list(locationsPaths.keys())
    return render_template("POS/Admin/locationAdmin.html",
                       restName=estNameStr,
                       LocName=LocName,
                       lenLocName=len(LocName),
                       currentLoc=location)



@app.route('/<location>/createMenu', methods=["POST"])
def meun1(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if ((idToken == database.get("restaurants/" + uid + "/" + location + "/", "LoginToken")) and (
            time.time() - database.get("restaurants/" + uid + "/" + location + "/", "LoginTime") < adminSessTime)):
        return render_template("createMenu1.html",
                               next=location + "/createMenu2",
                               back=location + "/adminpanel")
    else:
        return redirect(url_for('.login', location=location))


@app.route('/<location>/createMenu', methods=["POST"])
def createMenu(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if (checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location + "/createMenu2",
                           back=location + "/adminpanel")


@app.route('/<location>/createMenu2', methods=["POST"])
def createMenu2(location):
    idToken = session.get('token', None)
    fbToken = session.get('fbToken', None)
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    menuName = rsp["Name"]
    menuDays = rsp["Days"]
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    if (checkAdminToken(location) == 1):
        return redirect(url_for('.login', location=location))
    return render_template("createMenu1.html",
                           next=location + "/createMenu3",
                           back=location + "/adminpanel")


@app.route('/admin', methods=["GET"])
def pickLocation():
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    getSquare()
    locs = []
    for lc in locationsPaths:
        locs.append(locationsPaths[lc]["name"])
    return (render_template("pickLocation.html", btn="uid", locs=locs, len=len(locs)))


@app.route('/uid', methods=["POST"])
def pickLocation2():
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    locationPick = rsp["location"]
    authentication = firebase.FirebaseAuthentication('if7swrlQM4k9cBvm0dmWqO3QsI5zjbcdbstSgq1W',
                                                     'cajohn0205@gmail.com', extra={'id': dbid})
    database = firebase.FirebaseApplication("https://cedarchatbot.firebaseio.com/",
                                            authentication=authentication)
    return redirect(url_for('.login', location=locationPick))


##########CUSTOMER END###########

def getReply(msg, number):
    doc_ref = db.collection('restaurants').document('info')
    doc = doc_ref.get().to_dict()
    smsopen = doc["smsopen"]
    smsclosed  = doc["smsclosed"]
    closeTimeHr = int(smsclosed[0:2])
    closeTimeMin = int(smsclosed[3:5])
    openTimeHr = int(smsopen[0:2])
    openTimeMin = int(smsopen[3:5])
    closeCheck = float(closeTimeHr) + float(closeTimeMin / 100.0)
    openCheck = float(openTimeHr) + float(openTimeMin / 100.0)
    currentHour = float(datetime.datetime.now(tzGl[0]).strftime("%H"))
    currentMin = float(datetime.datetime.now(tzGl[0]).strftime("%M")) / 100.0
    currentTime = currentHour + currentMin
    if (openCheck <= currentTime <= closeCheck):
        msg = msg.lower()
        msg.replace("\n", "")
        msg.replace(".", "")
        msg.replace(" ", "")
        msg = ''.join(msg.split())

        if (msg == "order" or msg == "ordew" or msg == "ord" or msg == "ordet" or msg == "oderr" or msg == "ordee" or (
                "ord" in msg)):
            reply = "Hi welcome to " + estNameStr + "! click the link below to order \n" + str(
                mainLink) + "/smsinit/" + str(number)
            return reply
        else:
            return ("no msg")
    else:
        return ("no msg")

@app.route('/sms')
def inbound_sms():
    # Sender's phone number
    from_number = request.values.get('From')
    # Receiver's phone number - Plivo number
    to_number = request.values.get('To')
    # The text which was received
    text = request.values.get('Text')
    print('Message received - From: %s, To: %s, Text: %s' % (from_number, to_number, text))
    resp = getReply(text, from_number)
    print(str(resp))
    if (resp != "no msg"):
        client.messages.create(
            src=botNumber,
            dst=from_number,
            text=resp
        )
    return '200'

###Kiosk###

def genMenuData(location,menu):
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    #print(menuInfo)
    categories = list(menuInfo["categories"])
    baseItms = []
    descrips = []
    exInfo = []
    modsArr = []
    for itms in categories:
        #print(list(menuInfo["categories"][itms]))
        currArr = []
        currArr2 = []
        currArr3 = []
        currArr4 = []
        currArr5 = []
        for ll in range(len(list(menuInfo["categories"][itms]))):
            itmArr = []
            itx = (list(menuInfo["categories"][itms])[ll])
            itx2 = itx.replace(" ","-")
            currArr2.append([itx2,itx])
            descrip = (menuInfo["categories"][itms][itx]["descrip"])
            exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
            currArr4.append(exinfo)
            currArr3.append(descrip)
            modNames = (list(menuInfo["categories"][itms][itx])[2:])
            for mods in modNames:
                max = int(menuInfo["categories"][itms][itx][mods]["max"]) - int(menuInfo["categories"][itms][itx][mods]["min"])
                modArr = [mods,menuInfo["categories"][itms][itx][mods]["min"],max]
                opt = list(menuInfo["categories"][itms][itx][mods]["info"])
                modArr2 = []
                for oo in opt:
                    modArr2.append([oo,menuInfo["categories"][itms][itx][mods]["info"][oo]])
                modArr.append(modArr2)
            currArr5.append(modArr)
            modArr = []
            itmArr = []
        baseItms.append(currArr2)
        descrips.append(currArr3)
        exInfo.append(currArr4)
        modsArr.append([currArr5])
        currArr2 = []
        currArr3 = []
        currArr4 = []
        currArr5 = []

    #print(baseItms)
    #print(categories)
    #print(descrips)
    #print(exInfo)
    #print(modsArr)
    itmArr = [baseItms,categories,descrips,exInfo,modsArr]
    return itmArr

def findMenu(location):
    day = dayNames[int(datetime.datetime.now(tzGl[0]).weekday())]
    curMin = float(datetime.datetime.now(tzGl[0]).minute) / 100.0
    curHr = float(datetime.datetime.now(tzGl[0]).hour)
    curTime = curHr + curMin
    pathTime = '/restaurants/' + estNameStr + '/' + str(location) + "/schedule/" + day

    schedule = db.reference(pathTime).get()
    schedlist = list(schedule)
    start = 24
    sortedHr = [0]
    for scheds in schedlist:
        sortedHr.append(schedule[scheds])

    sortedHr.sort()
    sortedHr.append(24)
    for sh in range(len(sortedHr) - 1):
        if((sortedHr[sh]< curTime < sortedHr[sh+1])== True):
            menuKey = sh
            break


    for sh2 in range(len(schedlist)):
        if(sortedHr[menuKey] == schedule[schedlist[sh2]]):
            menu = (schedlist[sh2])
            break

    menuItems = []
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    categories = list(menuInfo["categories"])
    for itms in categories:
        #print(list(menuInfo["categories"][itms]))
        currArr = [itms]
        for ll in range(len(list(menuInfo["categories"][itms]))):
            itmArr = []
            itx = (list(menuInfo["categories"][itms])[ll])
            descrip = (menuInfo["categories"][itms][itx]["descrip"])
            exinfo = (menuInfo["categories"][itms][itx]["extra-info"])
            print(itms)
            itmArr.append(itx)
            itmArr.append(descrip)
            itmArr.append(exinfo)
            modNames = (list(menuInfo["categories"][itms][itx])[2:])
            for mods in modNames:
                modArr = [mods,menuInfo["categories"][itms][itx][mods]["min"],menuInfo["categories"][itms][itx][mods]["max"]]
                opt = list(menuInfo["categories"][itms][itx][mods]["info"])
                for oo in opt:
                    modArr.append([oo,menuInfo["categories"][itms][itx][mods]["info"][oo]])

                itmArr.append(modArr)
                modArr = []

            currArr.append(itmArr)
            itmArr = []
        menuItems.append(currArr)
    return(menuItems)

@app.route('/<location>/sitdown-startKiosk', methods=["GET"])
def startKiosk2(location):
    return(render_template("Customer/Sitdown/startKiosk.html",btn="startKiosk",restName=estNameStr,locName=location))


@app.route('/<location>/sitdown-startKiosk', methods=["POST"])
def startKiosk(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    table = rsp["table"]
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + str(location) + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    ref.set({
        orderToken : {
            "name":name,
            "phone":phone,
            "table":table,
             "timestamp":time.time()
        }
        })
    session['orderToken'] = orderToken
    #menu = findMenu(location)
    menu = "lunch"
    session["menu"] = menu
    #print(menu)
    pathMenu = '/restaurants/' + estNameStr + '/' + str(location) + "/menu/" + menu
    menuInfo = db.reference(pathMenu).get()
    print(menuInfo)
    categories = list(menuInfo["categories"])
    #cats = ['burgers','pizzas']
    #baseItms = [[['cheese-burger','cheese burger'],['chicken-sandwich','chicken sandwich']],[['combo-pizza','combo pizza']]]
    #descrips = [['kobe beef patty','grilled chicken'],['sausage, vegetables, and pepperoni']]
    #exInfo = [['contains meat',' '],['contains dairy']]
    mods = [[[["sizes",1,0,[['standard',6.55]]],["sides",1,0,[["bacon fries",1],["fries",0]]]] , [["sizes", 1,0,[["standard",6]]], ["toppings",0,2,[["bacon",1],["cheese",1]]]]], [ [["sizes",1,0,[["11 in", 9],["17 in", 11.25]]],["toppings", 0,2,[["extra cheese", 0.56],["extra pepperoni", 1]]]] ] ]
    menuData = genMenuData(location,menu)
    baseItms = menuData[0]
    cats = menuData[1]
    descrips = menuData[2]
    exInfo = menuData[3]
    #mods = menuData[4]
    print(baseItms)

    return(render_template("Customer/Sitdown/mainKiosk.html",cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,mods=mods,btn=str("sitdown-additms"),restName=estNameStr))


@app.route('/<location>/sitdown-additms', methods=["POST"])
def kiosk2(location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    print((rsp))
    return(str(rsp))
    cats = ['burgers','pizzas']
    baseItms = [[['cheese-burger','cheese burger'],['chicken-sandwich','chicken sandwich']],[['combo-pizza','combo pizza']]]
    descrips = [['kobe beef patty','grilled chicken'],['sausage, vegetables, and pepperoni']]
    exInfo = [['contains meat',' '],['contains dairy']]
    mods = [ [[["sizes",1,0,[['standard',6.55]]],["sides",1,0,[["bacon fries",1],["fries",0]]]] , [["sizes", 1,0,[["standard",6]]], ["toppings",0,2,[["bacon",1],["cheese",1]]]]], [ [["sizes",1,0,[["11 in", 9],["17 in", 11.25]]],["toppings", 0,2,[["extra cheese", 0.56],["extra pepperoni", 1]]]] ] ]
    return(render_template("Customer/Sitdown/mainKiosk.html",cats=cats,baseItms=baseItms,descrips=descrips,exInfo=exInfo,mods=mods,btn=str("sitdown-additms"),restName=estNameStr))



if __name__ == '__main__':
    try:
        getSquare()
        print(locationsPaths.keys())
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=200)
        app.debug = True
        app.run(host="0.0.0.0",port=5000)

    except KeyboardInterrupt:
        sys.exit()
