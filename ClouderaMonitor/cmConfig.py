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
from ldap3 import Server, Connection, ALL

def getActiveCMConfig(totalconfig):
    #Initialize dictionary to store configuration
    cmConfig = {}
    #Use CM API to retrieve Cloudera Manager config from each CM instance to be monitored
    for cm in totalconfig['cmfqdn']:
        api = ApiResource(cm,totalconfig[cm]['port'],totalconfig[cm]['user'],totalconfig[cm]['passwd'],totalconfig[cm]['tls'],totalconfig[cm]['apiv'])
        #Retrieve configuration for all services in all clusters in Cloudera Manager instance
        clusters = api.get_all_clusters()
        cmConfig[cm]={}
        for cluster in clusters:
            cmConfig[cm][cluster.displayName]={}
            services=cluster.get_all_services()
            for service in services:
                cmConfig[cm][cluster.displayName][service.name]={}
                cmConfig[cm][cluster.displayName][service.name]['Service']={}
                cmConfig[cm][cluster.displayName][service.name]['SERVICE TYPE']={'value':service.type}
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
        cmConfig[cm][cm + " Instance"]["CLOUDERA MANAGER"] = {}
        cmConfig[cm][cm + " Instance"]["CLOUDERA MANAGER"]['SERVICE TYPE']={'value': 'CLOUDERA MANAGER'}
        for name,config in cminstance.get_config(view='full').items():
            cmConfig[cm][cm + " Instance"]["CLOUDERA MANAGER"][name] = {'value':config.value,'default':config.default}
        #Retrieve Cloudera Management Service Instance
        cmsinstance = cminstance.get_service()
        cmConfig[cm][cm + " Instance"]['CLOUDERA MANAGEMENT SERVICES']={}
        cmConfig[cm][cm + " Instance"]['CLOUDERA MANAGEMENT SERVICES']['SERVICE TYPE']={'value': 'CLOUDERA MANAGEMENT SERVICES'}
        for name,config in cmsinstance.get_config(view='full')[0].items():
            cmConfig[cm][cm + " Instance"]['CLOUDERA MANAGEMENT SERVICES'][name]={'value':config.value,'default':config.default}
        for roleGroup in cmsinstance.get_all_role_config_groups():
            cmConfig[cm][cm + " Instance"][roleGroup.roleType]={}
            cmConfig[cm][cm + " Instance"][roleGroup.roleType]['SERVICE TYPE']={'value': roleGroup.roleType}
            for name,config in roleGroup.get_config(view='full').items():
                cmConfig[cm][cm + " Instance"][roleGroup.roleType][name]={'value':config.value,'default':config.default}
            print(roleGroup.roleType)
        #Get all CM Users and assigned roles
        cmConfig[cm][cm + " Instance"]["CM Users"] = {}
        for user in api.get_all_users():
            cmConfig[cm][cm + " Instance"]["CM Users"][user.name]={'roles':user.roles}
    #If configured, monitor membership of LDAP groups
    if totalconfig['ldapmonitor']['monitorgroups']:
        #Initialize dictionary for monitored group configuration
        cmConfig["Monitored Groups"] = {}
        try:
            ldapconn = getLDAPConnection(totalconfig['ldapmonitor'])
            if ldapconn != False:
                with open(totalconfig['ldapmonitor']['groupFile'],'r') as gf:
                    for group in gf:
                        cmConfig["Monitored Groups"][group] = getFirstLDAPGroup(ldapconn,group.strip(),totalconfig['ldapmonitor']['ldapSearchDN'])
        except LDAPException as e:
            print("ERROR: " + e)
            pass
        finally:
            ldapconn.unbind()
    return cmConfig

def getLDAPConnection(ldapconf):
    connect = Server(ldapconf['ldapServer'],int(ldapconf['ldapPort']),use_ssl=ldapconf['ldapTLS'])
    try:
        ldapconn = Connection(connect,ldapconf['ldapBindUser'],ldapconf['ldapBindPassword'],auto_bind=True)
    except LdapExceptionError as errval:
        print(errval)
        raise
    if ldapconf['ldapStartTLS']:
        ldapconn.start_tls()
    if ldapconn.bound:
        return ldapconn
    else:
        return False

def getLDAPGroupMembers(conn,dn,presentGroups):
    conn.search(dn,'(objectclass=group)','BASE',attributes=['member'])
    groups = {}
    for member in conn.entries[0].member:
        groups[member] = detailLDAPGroupMembers(conn,member,presentGroups)
    return groups
    
def detailLDAPGroupMembers(conn,name,presentGroups):
    conn.search(name,'(objectclass=*)','BASE',attributes=['samaccountname','name','objectcategory','distinguishedname'])
    userdict = {}
    if 'CN=Person' in conn.entries[0].objectcategory[0]:
        print("THIS IS A PERSON")
        userdict = {'samaccountname':conn.entries[0].samaccountname[0],'name':conn.entries[0].name[0],'objectcategory':conn.entries[0].objectcategory[0]}
    else:
        print("THIS IS A GROUP")
        if conn.entries[0].name[0] in presentGroups:
            print("GROUP ALREADY EXISTS")
            userdict = {'name':conn.entries[0].name[0],'objectcategory':conn.entries[0].objectcategory[0],'members': "WARNING: CIRCULAR NESTING"}
        else:
            presentGroups.append(conn.entries[0].name[0])
            userdict = {'name':conn.entries[0].name[0],'objectcategory':conn.entries[0].objectcategory[0],'members':getLDAPGroupMembers(conn,conn.entries[0].distinguishedname[0],presentGroups)}
    return userdict

def getFirstLDAPGroup(ldapconn,groupname,searchdn):
    print(ldapconn)
    ldapconn.search(searchdn,'(&(objectclass=group)(cn='+groupname+'))',attributes=['member'])
    if len(ldapconn.entries) == 1:
        memberdict = {groupname:{}}
        print(ldapconn.entries[0])
        for member in ldapconn.entries[0].member:
            print(member)
            presentGroups = []
            memberdict[groupname][member] = detailLDAPGroupMembers(ldapconn,member,presentGroups)
        return memberdict
    else:
        print('ERROR: Search for group \'' + groupname + '\' returned multiple results.')
        print(ldapconn.entries)

def loadCMConfig():
    with open("CMConfig.json",'r') as fc:
        cmConf = json.loads(fc.read())
        return cmConf

def saveActiveCMConfig(totalconfig):
    config = getActiveCMConfig(totalconfig)
    with open("CMConfig.json",'w') as f:
        json.dump(config,f,indent=4)

def getDictDiff(a,b,leftuniquename,rightuniquename):
    if isinstance(a,dict) and isinstance (b,dict):
        aunique = {}
        difference = {}
        bunique = {}
        aunique = getUnique(a,b)
        bunique = getUnique(b,a)
        
        difference = getDifference(a,b,leftuniquename,rightuniquename)
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
            

def getDifference(a,b,leftString,rightString):
    difference = {}
    for key in a.keys():
        if key in b.keys() and isinstance(a[key],dict) and isinstance(b[key],dict):
            difference[key] = getDifference(a[key],b[key],leftString,rightString)
        elif key in b.keys() and a[key] != b[key]:
            difference[key] = {leftString:a[key],rightString:b[key]}
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

def compareToBaseline(baseline,clusterConfig):
    #baseline will be at service name level
    #clusterConfig will be passed in at the Cluster level (i.e., result of "for cluster in cmConfig.keys()") 
    baselineComparison = {}
    #cmConfig[cm][cluster.displayName][service.name]['SERVICE TYPE']={'value':service.type}
    #cmConfig[cm][cluster.displayName][service.name][roleGroup.roleType][name]={'value':config.value,'default':config.default}
    if isinstance(baseline,dict) and isinstance(clusterConfig,dict):
        for cmInstance in clusterConfig.keys():
            baselineComparison[cmInstance] = {}
            print(baselineComparison)
            for clusterName in clusterConfig[cmInstance].keys():
                baselineComparison[cmInstance][clusterName]={}
                for service in clusterConfig[cmInstance][clusterName].keys():
                    if 'SERVICE TYPE' in clusterConfig[cmInstance][clusterName][service]:
                        if clusterConfig[cmInstance][clusterName][service]['SERVICE TYPE']['value'] in baseline:
                            baselineComparison[cmInstance][clusterName][service]=getDictDiff(baseline[clusterConfig[cmInstance][clusterName][service]['SERVICE TYPE']['value']],clusterConfig[cmInstance][clusterName][service],"Baseline","CurrentConfig")
                            baselineComparison[cmInstance][clusterName][service].pop("CurrentConfig_UNIQUE")
                        else:
                            baselineComparison[cmInstance][clusterName][service]="SERVICE NOT IN BASELINE"
    return baselineComparison