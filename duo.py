import requests
from flask import render_template, request
from app import app
from qpylib import qpylib
import logging
import time
import threading
import base64, email, hmac, hashlib, urllib, requests, json, syslog, socket

poll_time = 30000

@app.before_first_request
def activate_job():
    def run_job():
        global poll_time
        console_ip = qpylib.get_console_address()
        
        while True:
            print('Looking for logs')
            #getLogs()
            sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
            sock.sendto(json.dumps('Duo DSM heartbeat'), (console_ip, 514))
            time.sleep(poll_time/1000)

    thread = threading.Thread(target=run_job)
    thread.start()

@app.route('/admin_screen')
def admin_screen():
    return render_template("admin_screen.html")

def sign(method, host, path, params, skey, ikey):
    """
    Return HTTP Basic Authentication ("Authorization" and "Date") headers.
    method, host, path: strings from request
    params: dict of request parameters
    skey: secret key
    ikey: integration key
    """

    # create canonical string
    now = email.Utils.formatdate()
    canon = [now, method.upper(), host.lower(), path]
    args = []
    for key in sorted(params.keys()):
        val = params[key]
        if isinstance(val, unicode):
            val = val.encode("utf-8")
        args.append(
            '%s=%s' % (urllib.quote(key, '~'), urllib.quote(val, '~')))
    canon.append('&'.join(args))
    canon = '\n'.join(canon)

    # sign canonical string
    sig = hmac.new(skey, canon, hashlib.sha1)
    auth = '%s:%s' % (ikey, sig.hexdigest())

    # return headers
    return {'Date': now, 'Authorization': 'Basic %s' % base64.b64encode(auth)}

def getLogs():
    global poll_time
    console_ip = qpylib.get_console_address()
    
    # Get logs starting from 60 seconds ago through right now
    min_time= str(int(round(time.time() * 1000)) - poll_time)
    max_time = str(int(round(time.time() * 1000)))
    
    payload = {'mintime': min_time, 'maxtime': max_time}

    duo = sign('GET', 'api-########.duosecurity.com', '/admin/v2/logs/authentication', payload, 'enter-skey-here', 'enter-ikey-here')

    duo_auth = duo['Authorization']
    duo_date = duo['Date']

    # Make the request
    r = requests.get('https://api-########.duosecurity.com/admin/v2/logs/authentication', params=payload, headers={'Authorization': duo_auth, "Date":duo_date,'Content-Type':'application/x-www-form-urlencoded'})


    # Change the JSON string into a JSON object
    jsonObject = json.loads(r.text)
    if "response" in jsonObject:
        
        resp = jsonObject["response"]
        # Print the logs
        for MESSAGE in resp['authlogs']:
            sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP
            sock.sendto(json.dumps(MESSAGE), (console_ip, 514))
    elif "code" in jsonObject:
        # Print the errors
        sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
        sock.sendto(json.dumps(jsonObject['message']), (console_ip, 514))
        poll_time = poll_time + 30000
    else: