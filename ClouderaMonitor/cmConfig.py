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
        clusters = api.get_all_clusters()
        cmConfig[cm]={}
        for cluster in clusters:
            cmConfig[cm][cluster.displayName]={}
            services=cluster.get_all_services()
            for service in services:
                cmConfig[cm][cluster.displayName][service.name]={}
                cmConfig[cm][cluster.displayName][service.name]['Service']={}
                for name,config in service.get_config(view='full')[0].items():
                    cmConfig[cm][cluster.displayName][service.name]['Service'][name]={'value':config.value,'default':config.default}
                for roleGroup in service.get_all_role_config_groups():
                    cmConfig[cm][cluster.displayName][service.name][roleGroup.roleType]={}
                    for name,config in roleGroup.get_config(view='full').items():
                        cmConfig[cm][cluster.displayName][service.name][roleGroup.roleType][name]={'value':config.value,'default':config.default}
                    print(roleGroup.roleType)
    #print(json.dumps(cmConfig, indent=4))
    return cmConfig

def loadCMConfig():
    with open("CMConfig.json",'r') as fc:
        cmConf = json.loads(fc.read())
        return cmConf

def getHostsByService(totalconfig):
    serviceConfig = {}

def saveActiveCMConfig(totalconfig):
    config = getActiveCMConfig(totalconfig)
    with open("CMConfig.json",'w') as f:
        json.dump(config,f,indent=4)

def findDifferenceandIntersect(current,prior):
    currentUnique=(set(current.keys())).difference(set(prior.keys()))
    priorUnique=(set(prior.keys())).difference(set(current.keys()))
    keyIntersect=(set(current.keys())).intersection(set(prior.keys()))
    finalCurrent={}
    finalPrior={}
    finalIntersection={}
    for key in current.keys():
        if key in currentUnique:
            finalCurrent[key+'_UNIQUE']=current[key]
        else:
            finalCurrent[key]={}
    for key in prior.keys():
        if key in priorUnique:
            finalPrior[key+'_UNIQUE']=prior[key]
        else:
            finalPrior[key]={}
    for key in keyIntersect:
        finalIntersection[key]={}
    return finalCurrent,finalPrior,finalIntersection

def removeNonUnique(configDict):
    unique = "_UNIQUE"
    for host in configDict.keys():
        if unique not in host:
            for cluster in configDict[host].keys():
                if unique not in cluster:
                    for service in configDict[host][cluster].keys():
                        if unique not in service:
                            for role in configDict[host][cluster][service].keys():
                                if unique not in role:
                                    for setting in configDict[host][cluster][service][role].keys():
                                        if unique not in setting:
                                            del configDict[host][cluster][service][role][setting]
                                        if not bool(configDict[host][cluster][service][role]):
                                            del configDict[host][cluster][service][role]
                            if not bool(configDict[host][cluster][service]):
                                del configDict[host][cluster][service]
                        if not bool(configDict[host][cluster]):
                            del configDict[host][cluster]
                if not bool(configDict[host]):
                    del configDict[host]
    return configDict

def removeEmpty(configDict):
    for host in configDict.keys():
        for cluster in configDict[host].keys():
            for service in configDict[host][cluster].keys():
                for role in configDict[host][cluster][service].keys():
                    if not bool(configDict[host][cluster][service][role]):
                        del configDict[host][cluster][service][role]
                if not (bool(configDict[host][cluster][service])):
                    del configDict[host][cluster][service]
            if not bool(configDict[host][cluster]):
                del configDict[host][cluster]
        if not bool(configDict[host]):
                del configDict[host]
    return configDict

def compareConfigs(currentConfig,priorConfig):
    configReport = {}
    currentUnique = {}
    priorUnique = {}
    configIntersection = {}
    #configReport will be a dictionary that shows the full differences between configs. At the level the differences start, two keys will be present: "Current" and "Prior"
    #If differences are just in values then dictionary will look the same but values at the base will be "Current" and "Prior"
    
    currentUnique,priorUnique,configIntersection = findDifferenceandIntersect(currentConfig,priorConfig)
    for host in configIntersection.keys():
        currentUnique[host],priorUnique[host],configIntersection[host] = findDifferenceandIntersect(currentConfig[host],priorConfig[host])
        for cluster in configIntersection[host].keys():
            currentUnique[host][cluster],priorUnique[host][cluster],configIntersection[host][cluster] = findDifferenceandIntersect(currentConfig[host][cluster],priorConfig[host][cluster])
            for service in configIntersection[host][cluster].keys():
                currentUnique[host][cluster][service],priorUnique[host][cluster][service],configIntersection[host][cluster][service] = findDifferenceandIntersect(currentConfig[host][cluster][service],priorConfig[host][cluster][service])
                for role in configIntersection[host][cluster][service].keys():
                    currentUnique[host][cluster][service][role],priorUnique[host][cluster][service][role],configIntersection[host][cluster][service][role] = findDifferenceandIntersect(currentConfig[host][cluster][service][role],priorConfig[host][cluster][service][role])
                    for setting in configIntersection[host][cluster][service][role].keys():
                        currentUnique[host][cluster][service][role][setting],priorUnique[host][cluster][service][role][setting],configIntersection[host][cluster][service][role][setting] = findDifferenceandIntersect(currentConfig[host][cluster][service][role][setting],priorConfig[host][cluster][service][role][setting])
                        if currentConfig[host][cluster][service][role][setting] != priorConfig[host][cluster][service][role][setting]:
                            configIntersection[host][cluster][service][role][setting] = {'CURRENT':currentConfig[host][cluster][service][role][setting],'PRIOR':priorConfig[host][cluster][service][role][setting]}
                        else:
                            del configIntersection[host][cluster][service][role][setting]
    #Remove non-unique and empty values
    currentUnique = removeNonUnique(currentUnique)
    priorUnique = removeNonUnique(priorUnique)
    configIntersection = removeEmpty(configIntersection)

    configReport={'CURRENT_CONFIG_UNIQUE':currentUnique,'PRIOR_CONFIG_UNIQUE':priorUnique,'SETTINGS_DIFFERENCES':configIntersection}
    with open("ConfigReport.json",'w') as f:
        json.dump(configReport,f,indent=4)
    sendMail = False
    for configKey in configReport.keys():
        if bool(configReport[configKey]):
            print(configKey + "TRUE")
            sendMail = True
    if sendMail:
        return configReport
    else:
        return False