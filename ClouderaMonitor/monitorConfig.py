#   Copyright 2017 Christopher J. Morgan
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#Generate master configuration for Cloudera Manager Monitor
import re
import json
import socket
import smtplib


#Ask the user for configuration parameters
#Necessary Parameters: FQDN of Monitor Host, FQDNs of Cloudera Manager Hosts, CM Usernames, CM Passwords
#Construct dict dynamically for CM hosts, usernames and passwords 
#Create separate configs for Main Monitor Host and Node Agents
#TODO:Make configuration generation into function called from command line
def setMasterConfig():
    while True:
        hosts = raw_input("Input Cloudera Manager host FQDNs, separated by commas if multiple: ")
        if re.match('[a-zA-Z0-9.,]*(?<=[a-zA-Z0-9])\Z',hosts):
            break
        else:
            print("Error: Please ensure Cloudera Manager host FQDNs are properly formatted and separated by commas with no spaces.")

    cmhosts = hosts.split(",")
    cmhosts = [x.strip() for x in cmhosts]
    masterconfig = {}

    #For each CM host, query for parameters, create nested dict for host which includes FQDN, username, and password
    masterconfig['cmfqdn'] = cmhosts
    for host in masterconfig['cmfqdn']:
        while True:
            user = raw_input("Input Cloudera Manager API username for " + host + ": ")
            if re.match('[a-zA-Z0-9.]*\Z',user):
                break
            else:
                print("Error: Please ensure username is alphanumeric. The only special characters allowed are periods.")
    #TODO: Make password input secure: store with salted AES-256. Generate salt dynamically and store in config
        passwd = raw_input("Enter password for Cloudera Manager API user: ")
        while True:
            apiport = raw_input("Enter port on which CM API runs: ")
            if re.match('[\d]*\Z',apiport) and int(apiport)<65536:
                if int(apiport)<1024:
                    print("WARNING: Unusual port for API to be running on.") 
                break
            else:
                print("Error: Please ensure port consists only of digits")
	#TODO: Add regex for TLS
		tls = raw_input("Use TLS to connect to API? (Y/N): ")
        prefix = "http://"
		if (tls.upper()).startswith("Y"):
			prefix = "https://"
		masterconfig[host] = {
            'url': prefix + host,
			'user': user,
            'passwd': passwd,
            'port': apiport,
			'tls': (tls.upper()).startswith("Y")
        }

    #Query user for the port on which Master Monitor will run then get system FQDN
    while True:
        port = raw_input("Enter port on which Master Monitor will run: ")
        if re.match('[\d]*\Z',port) and int(port)<65536:
            if int(port)<1024:
                print("WARNING: Port is in the restricted range. Monitor must be running as root to listen on this port.") 
            break
        else:
            print("Error: Please ensure port consists only of digits")
    masterconfig['mastermonitorport'] = port
    masterconfig['mastermonitorfqdn'] = socket.getfqdn()

    with open("config.json",'w') as f:
        json.dump(masterconfig,f,indent=4)
    print(masterconfig)
    print("JSON")
    print(json.dumps(masterconfig, indent=4))

def getMasterConfig():
    with open("config.json",'r') as fc:
        masterconfg = json.loads(fc.read())
        return masterconfg

def createEmailHandler(server,port,username,passwd,starttls):
    mailHandler = smtplib.SMTP(server,port)
    if starttls:
        mailHandler.starttls()
    if not username:
        mailHandler.login(username,passwd)
    return mailHandler