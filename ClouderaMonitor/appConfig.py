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

#Generate master configuration for monitor app and create objects as necessary
import re
import json
import socket
import smtplib
import os
from base64 import b64encode
from email.MIMEMultipart import MIMEMultipart


#Ask the user for configuration parameters
#Necessary Parameters: FQDN of Monitor Host, FQDNs of Cloudera Manager Hosts, CM Usernames, CM Passwords
#Construct dict dynamically for CM hosts, usernames and passwords 
#TODO:Make configuration generation into function called from command line without running CM config comparison
def getSetting(question,matchre,errortext):
    while True:
        setting = raw_input(question)
        if 'TRUE/FALSE' in matchre:
            if re.match('[YNyn]\Z',setting):
                return (setting.upper()).startswith("Y")
            else:
                print(errortext)
        else:
            if re.match(matchre,setting):
                return setting
            else:
                print(errortext)

def setMasterConfig():
    while True:
        hosts = raw_input("Input Cloudera Manager host FQDNs or IP addresses, separated by commas if multiple: ")
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
        while True:
            tls = raw_input("Use TLS to connect to API? (Y/N): ")
            if re.match('[YNyn]\Z',tls):
                break
            else:
                print("Error: Please 'Y' or 'N'")
        while True:
            apiversion = raw_input("Enter API version number to use: ")
            if re.match('[\d]*\Z',apiversion) and int(apiversion)<40: 
                break
            else:
                print("Error: Please enter valid API version number")
        masterconfig[host] = {
            'user': user,
            'passwd': passwd,
            'port': apiport,
			'tls': (tls.upper()).startswith("Y"),
            'apiv': apiversion
        }
    masterconfig['hash']=getSetting("Hash passwords in configuration settings (Y/N)? ", 'TRUE/FALSE', "Error: Please enter Y or N.")
    masterconfig['hashsalt']=b64encode(os.urandom(64))
    #Query user for Active Directory monitoring information
    monitorAD = raw_input("Would you like to monitor Active Directory for changes to critical groups? (Y/N): ")
    if (monitorAD.upper()).startswith("Y"):
        while True:
            ldapServer = raw_input("Input Active Directory domain FQDN: ")
            if re.match('[a-zA-Z0-9.]*\Z',ldapServer):
                break
            else:
                print("Error: Please ensure FQDN is alphanumeric. The only special characters allowed are periods.")
        ldapBindUser = raw_input("Input bind account name. For Active Directory, input the account's userPrincipalName which typically takes the form of <USERNAME>@<DNS DOMAIN NAME>: ")
        ldapBindPassword = raw_input("Input bind account password: ")
        ldapSearchDN = raw_input("Input LDAP search base: ")
        while True:
            ldaptls = raw_input("Use TLS to connect to server? (Y/N): ")
            if re.match('[YNyn]\Z',ldaptls):
                ldapstarttls = 'N'
                break
            else:
                print("Error: Please enter 'Y' or 'N'")
        if (ldaptls.upper()).startswith("N"):
            while True:
                ldapstarttls = raw_input("Use StartTLS once server connection established? (Y/N): ")
                if re.match('[YNyn]\Z',ldapstarttls):
                    break
                else:
                    print("Error: Please enter 'Y' or 'N'")
        while True:
            ldapport = raw_input("Enter port number for LDAP connection: ")
            if re.match('[\d]*\Z',ldapport) and int(ldapport)<65536:
                if int(ldapport) != 389 and int(ldapport) != 636:
                    print("WARNING: Unusual port for LDAP protocol to be running on")
                break
            else:
                print("Please ensure port entered is numeric and below 65536")
        groupFile = raw_input("Enter name of text file from which to read group names to monitor: ")
        masterconfig['ldapmonitor'] = {
            'monitorgroups': True,
            'ldapServer': ldapServer,
            'ldapBindUser': ldapBindUser,
            'ldapBindPassword': ldapBindPassword,
            'ldapTLS': (ldaptls.upper()).startswith('Y'),
            'ldapStartTLS': (ldapstarttls.upper()).startswith('Y'),
            'groupFile': groupFile,
            'ldapPort': ldapport,
            'ldapSearchDN': ldapSearchDN
        }
    else:
        masterconfig['ldapmonitor'] = {
            'monitorgroups': False
        }
    #Query user for email configuration for alerts
    while True:
        baselineConf = raw_input("Compare current configuration to stored baseline? (Y/N): ")
        if re.match('[YNyn]\Z',baselineConf):
            if (baselineConf.upper()).startswith("Y"):
                masterconfig['baseline']=True
                masterconfig['baselineFile']=getSetting("Input baseline JSON file name: ",'[a-zA-Z0-9.]*\Z',"Error: Please enter a valid filename.")
                masterconfig['baselineGetCurrentUnique']=getSetting("Get current configuration items not in baseline (Y/N)? ",'TRUE/FALSE',"Error: Enter Y or N.")
            else:
                masterconfig['baseline']=False
            break
        else:
            print("Error: Please enter 'Y' or 'N'")
    sendalerts = raw_input("Would you like to send email alerts when changes are detected? (Y/N): ")
    if (sendalerts.upper()).startswith("Y"):
        while True:
            smtpserver = raw_input("Input SMTP Server FQDN (or 'N' for no alerts: ")
            if re.match('[a-zA-Z0-9.]*\Z',smtpserver):
                break
            else:
                print("Error: Please ensure SMTP server FQDN is alphanumeric. The only special characters allowed are periods.")
        while True:
            smtpport = raw_input("Enter SMTP Server Port: ")
            if re.match('[\d]*\Z',smtpport) and int(smtpport)<65536:
                commonsmtpports = [25, 465, 587]
                if int(smtpport) not in commonsmtpports:
                    print("WARNING: Unusual SMTP port.") 
                break
            else:
                print("Error: Please ensure port consists only of digits")
        #Add regex for smtpuser
        smtpuser = raw_input("Enter SMTP Server Username, or leave blank if unauthenticated: ")
        smtppass = ""
        if smtpuser:
            smtppass = raw_input("Enter SMTP Server password: ")
        while True:
            smtptls = raw_input("Use TLS to connect to STMP Server? (Y/N): ")
            if re.match('[YNyn]\Z',smtptls):
                break
            else:
                print("Error: Please enter 'Y' or 'N'")
        while True:
            mailfrom = raw_input("Input Alert E-Mail 'FROM' Address: ")
            if re.match('[a-zA-Z0-9.@]*\Z',mailfrom):
                break
            else:
                print("Error: Please ensure from address is alphanumeric. The only special characters allowed are periods and @.")
        while True:
            mailto = raw_input("Input Alert E-Mail 'TO' Addresses, separated by commas without spaces: ")
            if re.match('[a-zA-Z0-9,.@]*\Z',mailfrom):
                break
            else:
                print("Error: Please ensure To addresses are correct. The only special characters allowed are periods and @.")
        masterconfig['alerts'] = {
            'sendalerts': True,
            'smtpserver': smtpserver,
            'smtpport': smtpport,
            'smtpuser': smtpuser,
            'smtppass': smtppass,
            'smtptls': (smtptls.upper()).startswith("Y"),
            'emailfrom': mailfrom,
            'emailto': mailto.split(',')
        }

    else:
        masterconfig['alerts'] = {
            'sendalerts': False
        }
    #Future Functionality: Central monitor node will listen for agent monitors' node reports
    #Query user for the port on which Master Monitor will run then get system FQDN
    #while True:
    #    port = raw_input("Enter port on which Master Monitor will run: ")
    #    if re.match('[\d]*\Z',port) and int(port)<65536:
    #        if int(port)<1024:
    #            print("WARNING: Port is in the restricted range. Monitor must be running as root to listen on this port.") 
    #        break
    #    else:
    #        print("Error: Please ensure port consists only of digits")
    #masterconfig['mastermonitorport'] = port
    #masterconfig['mastermonitorfqdn'] = socket.getfqdn()

    with open("config.json",'w') as f:
        json.dump(masterconfig,f,indent=4)
    print(masterconfig)
    print("JSON")
    print(json.dumps(masterconfig, indent=4))

def getMasterConfig():
    with open("config.json",'r') as fc:
        masterconfg = json.loads(fc.read())
        return masterconfg

def getBaselineConfig(baselineFile):
    with open(baselineFile,'r') as fc:
        baselineconfg = json.loads(fc.read())
        return baselineconfg

def createEmailHandler(alertconfig):
    mailHandler = smtplib.SMTP(alertconfig['smtpserver'],int(alertconfig['smtpport']))
    if alertconfig['smtptls']:
        mailHandler.starttls()
    if alertconfig['smtpuser']:
        mailHandler.login(alertconfig['smtpuser'],alertconfig['smtppass'])
    message = MIMEMultipart()
    message['From'] = alertconfig['emailfrom']
    message['To'] = ','.join(alertconfig['emailto'])
    message['Subject'] = "Cloudera Manager Configuration Comparison Report"
    return mailHandler,message