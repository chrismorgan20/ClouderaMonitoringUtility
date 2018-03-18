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

#Cloudera Manager Monitoring Agent

#import standard libraries
import smtplib
from email.MIMEText import MIMEText
import json

#import third-party libraries
from pathlib import Path
import cm_api

#import local source
import appConfig
import cmConfig

#Check if prior app config exists, if not, enter setup mode
if not Path("config.json").is_file():
    print("Monitor Configuration not found. Entering setup...")
    appConfig.setMasterConfig()
#Load Monitor Configuration
config = appConfig.getMasterConfig()

#Check if previous Cloudera Monitor configuration has been extracted and saved to disk
if not Path("CMConfig.json").is_file():
    print("No previous Cloudera Manager configuration extract. Performing first extract...")
    cmConfig.saveActiveCMConfig(config)
print("Retrieving Current Configuration...")
activeconfig=cmConfig.getActiveCMConfig(config)
storedconfig=cmConfig.loadCMConfig()

print("Comparing previous saved configuration with current active configuration...")
#Old working function
#compareResults = cmConfig.compareConfigs(activeconfig,storedconfig)
configReport = cmConfig.getDictDiff(storedconfig,activeconfig,'PRIOR_CONFIG','CURRENT_CONFIG')
#Save configReport to disk as JSON
cmConfig.saveReport(configReport,'ConfigReport.json')
#Check if configReport found no setting differences or uniquenesses
compareResults = cmConfig.checkIfEmptyReport(configReport)
print(configReport)

#Check if config says to monitor baseline
if config['baseline']:
    baseline = appConfig.getBaselineConfig(config['baselineFile'])
    baselineReport = cmConfig.compareToBaseline(baseline,activeconfig,config['baselineGetCurrentUnique'])
    print(json.dumps(baselineReport,indent=4))
    cmConfig.saveReport(baselineReport,'BaselineReport.json')

if compareResults and config['alerts']['sendalerts']:
    print("Differences found between configurations. Emailing results...")
    mail,msg = appConfig.createEmailHandler(config['alerts'])
    msg.attach(MIMEText(json.dumps(compareResults,indent=4), 'plain'))
    try:
        mail.sendmail(config['alerts']['emailfrom'],config['alerts']['emailto'],msg.as_string())
    except SMTPRecipientsRefused:
        print("ERROR: All Recipients refused by server")
    except SMTPHeloError:
        print("ERROR: SMTP Helo error")
    except SMTPSenderRefused:
        print("ERROR: SMTP Sender Refused by server")
    except SMTPDataError:
        print("ERROR: Unspecified SMTP Data Error")
    mail.quit()