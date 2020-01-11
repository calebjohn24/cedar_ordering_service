import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import os
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort
from google.cloud import storage
import pytz
from flask import Flask, flash, request, session, jsonify
from werkzeug.utils import secure_filename
from flask import redirect, url_for
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from Cedar import collect_menu
from Cedar.admin import admin_panel
from Cedar.admin.admin_panel import checkLocation, sendEmail, getSquare



qsr_menu_blueprint = Blueprint('qsr_menu', __name__,template_folder='templates')

mainLink = 'https://033d08d3.ngrok.io/'




@qsr_menu_blueprint.route('/<estNameStr>/<location>/qsr-startKiosk', methods=["GET"])
def startKiosk4(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("Customer/QSR/startKiosk.html",btn="qsr-startKiosk",restName=estNameStr,locName=location))


@qsr_menu_blueprint.route('/<estNameStr>/<location>/qsr-startKiosk', methods=["POST"])
def startKioskQsr(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    print(togo)
    if(togo == "here"):
        table = "Table #" + rsp["table"]
        print(table)
    else:
        table = "To Go"
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":0,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(estNameStr,location)
    # menu = "lunch"
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@qsr_menu_blueprint.route('/<estNameStr>/<location>/qsr-menudisp')
def qsrMenu(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    # print(cart)
    return(render_template("Customer/QSR/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), cart=cart, locName=location.capitalize()))

@qsr_menu_blueprint.route('/<estNameStr>/<location>/qsr-additms~<cat>~<itm>', methods=["POST"])
def kiosk2QSR(estNameStr,location,cat,itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    ##print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = int(qty_str)
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                dispStr += str(raw_arr[0]).capitalize() + " "
                mods.append([raw_arr[0],raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    dispStr += "  |Notes: " +notes + "  (" + "${:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    ##print(orderToken)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat':cat,
        'itm':itm,
        'qty':qty,
        'img':img,
        'notes':notes,
        'price':price,
        'mods':mods,
        'unitPrice':unitPrice,
        'dispStr':dispStr
    })
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@qsr_menu_blueprint.route('/<estNameStr>/<location>/qsr-itmRemove', methods=["POST"])
def kioskRemQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    cartData = db.reference(pathCartitm).get()
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@qsr_menu_blueprint.route('/<estNameStr>/<location>/cartAdd-QSR', methods=["POST"])
def kioskCartQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    tableNum = db.reference(pathTable).get()
    menuInfo = db.reference(pathMenu).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        test = str(list(cart.keys()))
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        cpnBool = orderInfo["cpn"]
        if(cpnBool == 0):
            cart = dict(orderInfo["cart"])
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                if("discount" == str(cart[keys]["cat"])):
                    pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/" + keys
                    pathRemRef = db.reference(pathRem)
                    pathRemRef.delete()
        return(render_template("Customer/QSR/receipt.html"))
        # return(redirect(url_for("payQSR",estNameStr=estNameStr,location=location)))
    except Exception:
        return(redirect(url_for("qsrMenu",estNameStr=estNameStr,location=location)))

@qsr_menu_blueprint.route('/<estNameStr>/<location>/recipt-qsr', methods=["POST"])
def reciptQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    orderToken = session.get('orderToken',None)
    if(rsp['email'] != ""):
        userRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email":rsp['email']
        })
    else:
        userRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email":"no-email"
        })
    return(redirect(url_for("payQSR",estNameStr=estNameStr,location=location)))
