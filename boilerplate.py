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
            getLogs()
            sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
            sock.sendto(json.dumps('Heartbeat'), (console_ip, 514))
            time.sleep(poll_time/1000)

    thread = threading.Thread(target=run_job)
    thread.start()

@app.route('/admin_screen')
def admin_screen():
    return render_template("admin_screen.html")

def getLogs():
    global poll_time
    console_ip = qpylib.get_console_address()
    
    # Get logs starting from 60 seconds ago through right now
    min_time= str(int(round(time.time() * 1000)) - poll_time)
    max_time = str(int(round(time.time() * 1000)))
    
    payload = {'mintime': min_time, 'maxtime': max_time}


    # Make the request
    r = requests.get('https://api.example.com', params=payload)


    # Change the JSON string into a JSON object
    jsonObject = json.loads(r.text)
    # This assumes the valid logs will include "response"
    # And invalid logs include "code"
    # Modify as needed
    if "response" in jsonObject:
        
        resp = jsonObject["response"]
        # Convert the logs to syslog and feed to QRadar
        for MESSAGE in resp['authlogs']:
            sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP
            sock.sendto(json.dumps(MESSAGE), (console_ip, 514))
    elif "code" in jsonObject:
        # Feed the errors to QRadar
        sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
        sock.sendto(json.dumps(jsonObject['message']), (console_ip, 514))
        poll_time = poll_time + 30000
    else: