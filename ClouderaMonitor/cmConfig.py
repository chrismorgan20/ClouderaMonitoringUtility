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

from cm_api.api_client import ApiResource
import json

def getActiveCMConfig(totalconfig):
    cmConfig = {}
    for cm in totalconfig['cmfqdn']:
        api = ApiResource(cm,totalconfig[cm]['port'],totalconfig[cm]['user'],totalconfig[cm]['passwd'],totalconfig[cm]['tls'],totalconfig[cm]['apiv'])
        #Retrieve configuration for all clusters in Cloudera Manager instance
        clusters = api.get_all_clusters()
        cmConfig[cm]={}
        for cluster in clusters:
            cmConfig[cm][cluster.displayName]={}
            services=cluster.get_all_services()
            for service in services:
                cmConfig[cm][cluster.displayName][service.name]={}
                cmConfig[cm][cluster.displayName][service.name]['Service']={}
                cmConfig[cm][cluster.displayName][service.name]['Service']['SERVICE TYPE']={'value':service.type}
                for name,config in service.get_config(view='full')[0].items():
                    cmConfig[cm][cluster.displayName][service.name]['Service'][name]={'value':config.value,'default':config.default}
                for roleGroup in service.get_all_role_config_groups():
                    cmConfig[cm][cluster.displayName][service.name][roleGroup.roleType]={}
                    for name,config in roleGroup.get_config(view='full').items():
                        cmConfig[cm][cluster.displayName][service.name][roleGroup.roleType][name]={'value':config.value,'default':config.default}
                    print(roleGroup.roleType)
        #Retrieve configuration for Cloudera Manager instance
        cminstance = api.get_cloudera_manager()
        #Setup dictionaries for CM Settings
        cmConfig[cm][cm + " Instance"] = {}
        cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"] = {}
        cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]["CM Settings"] = {}
        for name,config in cminstance.get_config(view='full').items():
            cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]["CM Settings"][name] = {'value':config.value,'default':config.default}
        #Retrieve Cloudera Management Service Instance
        cmsinstance = cminstance.get_service()
        cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]['CMS Service']={}
        for name,config in cmsinstance.get_config(view='full')[0].items():
            cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]['CMS Service'][name]={'value':config.value,'default':config.default}
        for roleGroup in cmsinstance.get_all_role_config_groups():
            cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"][roleGroup.roleType]={}
            for name,config in roleGroup.get_config(view='full').items():
                cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"][roleGroup.roleType][name]={'value':config.value,'default':config.default}
            print(roleGroup.roleType)
        #Get all CM Users
        cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]["CM Users"] = {}
        for user in api.get_all_users():
            cmConfig[cm][cm + " Instance"]["Cloudera Manager Configuration"]["CM Users"][user.name]={'roles':user.roles}
    return cmConfig

def loadCMConfig():
    with open("CMConfig.json",'r') as fc:
        cmConf = json.loads(fc.read())
        return cmConf

def saveActiveCMConfig(totalconfig):
    config = getActiveCMConfig(totalconfig)
    with open("CMConfig.json",'w') as f:
        json.dump(config,f,indent=4)

#### NEW DICTIONARY COMPARISON FUNCTIONS #### STILL NEED TO COMPARE DIFFERENCES BETWEEN FUNCTIOS --- sendmail and write config is in old function at least

def getDictDiff(a,b,leftuniquename,rightuniquename):
    if isinstance(a,dict) and isinstance (b,dict):
        aunique = {}
        difference = {}
        bunique = {}
        aunique = getUnique(a,b)
        bunique = getUnique(b,a)
        
        difference = getDifference(a,b)
        # _UNIQUE will be added to the end of the leftunique and rightunique strings. This is meant to account for use of this function in other comparisons
        configReport = {leftuniquename+"_UNIQUE":removeNonUnique(aunique), rightuniquename+"_UNIQUE":removeNonUnique(bunique), "SETTINGS_DIFFERENCES":difference}
        return configReport
        
def saveReport(configDict,saveName):
    with open(saveName,'w') as f:
        json.dump(configDict,f,indent=4)
    
def checkIfEmptyReport(configDict):
    sendMail = False
    for configKey in configDict.keys():
        if bool(configDict[configKey]):
            sendMail = True
    if sendMail:
        return configDict
    else:
        return False

def removeNonUnique(unique):
    uniqueend = {}
    for key in unique.keys():
        if "_UNIQUE" in key:
            uniqueend[key] = unique[key]
        elif isinstance(unique[key],dict):
            uniqueend[key] = removeNonUnique(unique[key])
        if not uniqueend[key]:
            uniqueend.pop(key)
    return uniqueend
            

def getDifference(a,b):
    difference = {}
    for key in a.keys():
        if key in b.keys() and isinstance(a[key],dict) and isinstance(b[key],dict):
            difference[key] = getDifference(a[key],b[key])
        elif key in b.keys() and a[key] != b[key]:
            difference[key] = {'Left Value':a[key],'Right Value':b[key]}
    for key in difference.keys():
        if not difference[key]:
            difference.pop(key)
    return difference

def getUnique(a,b):
    aunique = {}
    for key in a.keys():
        if key in b.keys():
            if isinstance(a[key],dict) and isinstance(b[key],dict):
                aunique[key] = getUnique(a[key],b[key])
            #elif key in b.keys() and not isinstance(b[key],dict):
        else:
            aunique[key+"_UNIQUE"] = a[key]
    return aunique