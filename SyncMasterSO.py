from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from datetime import datetime
from datetime import timedelta
from apiclient import errors
from apiclient.http import MediaFileUpload, MediaIoBaseDownload
from oauth2client.file import Storage
import csv
import logging
import io
#from apiclient.http import MediaIoBaseDownload
from operator import itemgetter


# ========== CLASSES
class TeamDrive:
    # ItemList: object

    def __init__(self, name):
        self.name = name
        # self.id =
        self.ItemList = []

        # SCOPES = 'https://www.googleapis.com/auth/drive'
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('client_id.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.drive_service = build('drive', 'v3', http=creds.authorize(Http()))

        page_token = None
        # bepaal het Id van de teamdrive
        while True:
            response = self.drive_service.teamdrives().list(
                q="name = '" + self.name + "'",
                fields='nextPageToken, teamDrives(id, name)',
                useDomainAdminAccess=True,
                pageToken=page_token).execute()

            for team_drive in response.get('teamDrives', []):
                # print('Found Team Drive : %s (%s)' % (team_drive.get('name'), team_drive.get('id')))
                self.id = team_drive.get('id')
                print(self.id)

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        # build self.itemlist based on the TeamdriveId
        # the itemlist contains id, name, parents, mimetype and modiefiedtime of all the items in the teamdrive
        temp = []
        resultpage = []
        result = []
        page_token = None
        while True:
            result = self.drive_service.files().list(
                corpora='teamDrive',
                # q="mimeType != 'Aapplication/vnd.google-apps.folder' and trashed = False",
                q="trashed = False",
                pageSize=1000,
                teamDriveId=self.id,
                supportsTeamDrives=True,
                includeTeamDriveItems=True,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, parents, mimeType, modifiedTime)").execute()
            resultpage = result.get('files', [])

            # voeg de resultaten toe aan de tijdelijke lijst!!!
            for item in resultpage:
                self.ItemList.append(item)

            page_token = result.get('nextPageToken')
            if page_token is None:
                break
        ## add the fullpath- to the itemlist
        self.AddFullPathToItemlist()

    def AddFullPathToItemlist(self):
        #add the fullpath to the itemlist. Fullpath is the filenamefollowed bij de parent folders up to the teamdrive root
        #this string forms a unique id that allows the script to determine the position in the tree so it can be duplicated
        # to another teamdrive X:

        parentpath = []
        for item in self.ItemList:
            parentpath = self.GetParentNameTreeById(item['id'])
            parentpath.insert(0, item['name'])  # insert name in first position
            # reverse the list so order is top->bottom and store in itemlist in key 'fullpath'
            item.update({'fullpath': list(reversed(parentpath))})


    def PrintItemList(self):
        # Print all the items in the itemlist (= teamdrive contents)
        i = 0
        print('start printing the itemlist')
        for item in self.ItemList:
            print(u'{0} ({1}) ({2}) ({3}) ({4})'.format(item['name'], item['id'], item['parents'], item['mimeType'],
                                                        item['fullpath']))
            i = i + 1
        print(i)
        print(self.ItemList.__len__())


    def GetFolderContent(self, parentid, Mtype):
        # lookup all items with id = folderid in self.itemlist() and
        #  return a dict with the items found
        result = []
        if not self.ItemList:
            print('No itemlist found.')
            return 0
        else:
            i = 0
            # print('Files in itemlist:')
            for item in self.ItemList:
                # print(item'parents'])
                # als parents het partentid bevat en
                if Mtype == 'folder':
                    if (parentid in item['parents']) and ('application/vnd.google-apps.folder' in item['mimeType']):
                        result.append(item)
                        # print(u'{0} ({1}) ({2}) ({3})'.format(item['name'], item['id'], item['parents'], item['mimeType']))

                #elif Mtype == 'files':
                #    if (parentid in item['parents']):
                #       if not 'application/vnd.google-apps.folder' in item['mimeType']:
                #          result.append(item)
                #          print(u'{0} ({1}) ({2}) ({3})'.format(item['name'], item['id'], item['parents'], item['mimeType']))

                elif Mtype == 'all':
                    if parentid in item['parents']:
                        result.append(item)
                        # print(u'{0} ({1}) ({2}) ({3})'.format(item['name'], item['id'], item['parents'],item['mimeType']))
                else:
                    print('Argument not folder, files or all')
                i = i + 1
        return result

    def GetFolderTreeContent(self, parentid, Mtype):
        # buildt a recursive list of all the sub-items in a Folder and subfolders

        resulttree = []
        item1 = []
        for folder in self.GetFolderContent(parentid, Mtype):
            print(u'{0} ({1}) ({2})'.format(folder['name'], folder['id'], folder['parents']))
            resulttree.append(folder)

            for item1 in self.GetFolderTreeContent(folder['id'], Mtype):
                resulttree.append(item1)

        return resulttree


    def GetParentById(self, Id):
        # Return the Parent of an item based on the ItemId
        # Teamdrives support only 1 parent so returning 1 value is ok. Id the return value is emp
        result = []

        # zoek in de itemlist naar een item met id
        for item in self.ItemList:
            if Id in item['id']:
                result = item['parents']
        return result

    def GetParentTreeById(self, Id):
        # return a list with the Id's of the parent, the parent partens, ... of an item based on the itemId
        resulttree = []
        item = Id
        parent = ""

        while True:
            # get the parent of Id
            parent = self.GetParentById(item)

            if parent != "":
                # print(parent[0])
                resulttree.append(parent[0])
                item = parent[0]
            else:
                break
        return resulttree

    def GetNameById(self, id):
        # return the name of an item in the teamdrive based on it's id
        result = []
        # zoek in de itemlist naar een item met id
        for item in self.ItemList:
            if id in item['id']:
                result = item['name']
        return result

    def GetmimeType(self, id):
        result = []
        # zoek in de itemlist naar een item met id
        for item in self.ItemList:
            if id in item['id']:
                result = item['mimeType']
        return result

    def GetItemDetailsByID(self, id):
        result = []
        # zoek in de itemlist naar een item met id
        for item in self.ItemList:
            if id in item['id']:
                result = item
        return result

    def GetParentNameTreeById(self, Id):
        resulttree = []
        item = Id
        parent = ""

        while True:
            # get the parent of Id
            parent = self.GetParentById(item)

            if parent != "":
                # print(parent[0])
                name = self.GetNameById(parent[0])

                if len(name) != 0:
                    resulttree.append(name)
                    item = parent[0]
                else:
                    break
            else:
                break
        return resulttree

    def GetIdByFullPath(self, fullpath):

        fullpathlist = []
        fullpathlist.append(fullpath)

        for item in self.ItemList:
            #if item['fullpath'] == fullpathlist:  code for folderpair init
            if item['fullpath'] == fullpath:
                #result = item['id']
                return item['id']
              # break

    def getfullpathbyid(self, id):

       if id == self.id:
           return self.id

       for item in self.ItemList:
          if item['id'] == id:
          # result = item['id']
             return item['fullpath']
            # break




    # ========== folder and file manipulations

    def createfolder(self, name, parent):
        body = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent]}
        return self.drive_service.files().create(
            body=body,
            supportsTeamDrives=True,
            fields='id').execute().get('id')

    def createfolderwithparents(self,fullpath):

        #fullpathlist = []
        #fullpathlist.append(fullpath)

        currentpath = []
        foldername=""
        i=0
        newid=""
        parentdidexist=True
        parent = self.id   # highest level id = id of teamdrive

        #start with folder on highest level
        #while  i < len(fullpath[0]): code without list
        while i < len(fullpath):
           folderfound = False
           foldername = fullpath[i]
           currentpath.append(foldername)

           if parentdidexist == True:
              # if the parent of this folder existed, continue with checking the folder, if not
              # the lower level folders can be created without further checking

              for item in self.ItemList:
                  # search in the td's itemlist for an identical fullpath. If not found, the folder needs
                  # needs to be created
                 if item['fullpath'] == currentpath[0]:
                    folderfound = True

           if folderfound == False:
              parent = self.createfolder(foldername, parent)
              parentdidexist = False
           i += 1


    def deletefolder(self, id):
        self.drive_service.files().delete(fileId=id, supportsTeamDrives=True).execute()

    def deletefolderwithchilderen(self,fullpath):
        #delete the folder with this and all the child folders and files

        #first delete the files
        id = self.GetIdByFullPath(fullpath)
        itemlist = self.GetFolderTreeContent(id, 'all')
        folderlist =[]

        for item in itemlist:
           if item['mimeType'] != 'application/vnd.google-apps.folder':
              print(item)
              self.deletefile(item['id'])

              # !! remove the files from het self.ItemList but leave in this itemlist.
              self.ItemList.remove(item) # !! remove the files from het self.ItemList
           else:
               folderlist.append(item)

        #next, delete the folders but start with the 'lowest' level folders
        #so order the folderlist so the folders with the most parent folders will be deleted first

        sortedlist = sorted(folderlist, key=lambda x: len(x['fullpath']), reverse=True)

        for folder in sortedlist:
            self.deletefolder(folder['id'])
            self.ItemList.remove(folder)  # !! remove the files from het self.ItemList

        #remove the top folder
        self.deletefolder(id)

        #the end


    def deletefile(self, id):
        self.drive_service.files().delete(fileId=id, supportsTeamDrives=True).execute()


    def uploadfile(self, fullpath, parent):  # to do: make filename variable and source an destpath
        file_metadata = {
            'name': 'photo.jpg',
            'mimeType': '*/*',
            'parents': [parent]
        }
        media = MediaFileUpload(fullpath,
                                mimetype='*/*',
                                resumable=True)
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            supportsTeamDrives=True,
            fields='id').execute()
        print('File ID: ' + file.get('id'))


    def copyfile(self, id, parentid):
    # copy file with id on src to id of the parent destinationfolder.
    # the parentid can be locatated on another teamdrive

       filedetails = self.GetItemDetailsByID(id)

     # onderstaande nog te finetunen
       if filedetails['mimeType'] != 'application/vnd.google-apps.folder':
          operation_body = {
             'name': filedetails['name'],
             'parents': [parentid]}
          results = self.drive_service.files().copy(
             fileId=id,
             body=operation_body,
             supportsTeamDrives=True).execute()

          id_newfile = results.get("id")
          name_newfile = results.get("name")
          print(id_newfile, name_newfile)
       else:
          print('this is a folder')

# =========  FOLDERPAIR ====================================
class folderpair:
    def __init__(self, topfolderpath, sourcedrive, destdrive):
        self.name = "name"
        self.toppath = topfolderpath
        self.sourcetd = sourcedrive
        self.desttd = destdrive

        self.topfolderidsource = self.sourcetd.GetIdByFullPath(self.toppath)
        self.topfolderiddest = self.desttd.GetIdByFullPath(self.toppath)

        self.sourcefoldertree = self.sourcetd.GetFolderTreeContent(self.topfolderidsource)
        self.destfoldertree = self.desttd.GetFolderTreeContent(self.topfolderiddest)

    def ListMaster(self):
        print('in listmaster')
        self.sourcetd.PrintItemList()


    def syncfolders(self):
        # 1. First, Sync the folders
        # cycle trough SourceItemList and look for folders with the same fullpath in Destionation Itemlist
        # if destionation item found -> if modified time is equal -> do nothing;
        folderfound = False

        for srcitem in self.sourcefoldertree:
            print(srcitem['fullpath'])

            for dstitem in self.destfoldertree:
                # check if srcitem exists in same locatin in dstfolder

                if dstitem['fullpath'] == srcitem['fullpath']:
                   print('bingo, gevonden!')
                   folderfound = True

                if folderfound == False :
                   self.desttd.createfolderwithparents(srcitem['fullpath'])

        #2. check is a folder exists in dest but not anymore in src
                # this should be handled via the actionlog






    def syncfiles(self):

        # 1. First, Sync the folders
        # cycle trough SourceItemList and look for folders with the same fullpath in Destionation Itemlist
        # if destionation item found -> if modified time is equal -> do nothing;
        for srcitem in self.sourcefoldertree:
            # print(srcitem['fullpath'])

            for dstitem in self.destfoldertree:
               # check if srvitem exists in same locatin in dstfolder
 
                if dstitem['fullpath'] == srcitem['fullpath']:
                    print('bingo, gevonden!')
                    # if so, check if the lastmodified date in src

                    diff = ModTimeStamp(srcitem['modifiedTime']) - ModTimeStamp(dstitem['modifiedTime'])
                    delta = diff.total_seconds()

                    if delta == 0:  # timestamps are equal -> no action
                        print('timestamps are equal')
                    elif delta < 0:  # update
                        print('opgelet : src jonger dan dst')
                    elif delta > 0:  # opgelet:
                        print('update required')

            ## hierboven verder aanvullen om actionlog te updaten


class actionlog:

    # possible actions to add to the log:
    # copyfile(srctd,itemid,dsttd)  : copy file from srctd to same locatin on dst td)
    # deletefile(td,itemid) : delete the file with id on teamdrive td
    # makedir(td,fullpath) : create a folder on teamdrive td on location fullpath. Last item fullpath is foldenname
    # deletedir(td, fullpath) : remove the folder with fullpath on teamdrive td


    # actionlog is a list with actions
    # every action is appended as a dict containing the action and the other parameters required to perform the action

    # once the actionlog is constructed, the actions in the actionlog can be executed manually, automatically or
    # only when a certain security threshold ( %changes in relation to total items is smaller than ...) is not passed

    def __init__(self):
        self.actionlog=[]   #actionloglist

    def add_copyfile(self, srctd, itemid, dsttd):
        action = {}

        action = {'action':'copyfile', 'srctd':srctd, 'id':itemid, 'dsttd':dsttd }
        self.actionlog.append(action)
        return

    def add_deletefile(self, td, itemid):
        action = {}

        action = {'action':'deletefile', 'td':td, 'id':itemid }
        self.actionlog.append(action)
        #print('ff wachten')
        return

    def add_makedir(self, td, fullpath):
        action = {}

        action = {'action':'makedir', 'td':td, 'fullpath':fullpath }
        self.actionlog.append(action)
        #print('ff wachten')
        return

    def add_deletedir(self, td, fullpath):
        action = {}

        action = {'action':'deletedir', 'td':td, 'fullpath':fullpath }
        self.actionlog.append(action)
        #print('ff wachten')
        return


    def process(self,threshold=10,dryrun=False):
       #process the actionlog

       for action in self.actionlog:
           if action['action'] == 'copyfile':
              srctd = action['srctd']
              id = action['id']
              dsttd = action['dsttd']

              #parent in copyfile is het id of the folder in dsttd where dstfullpath == srcfullpath

              srcitemdetail = srctd.GetItemDetailsByID(id) # get the item details
              srcitemparent = srcitemdetail['parents'][0]  # extract the id of the src parentfolder
              srcitemparentfullpath = srctd.getfullpathbyid(srcitemparent)    # get the fullpath of the srcparentfolder

              if srcitemparent == srctd.id:  #if the file is located in the root of the td, then copy it to the root td
                  destpartentid = dsttd.id
              else:
                  #get the id of the parent folder in de dsttd where the fullpath matches the fullpath of the items parent

                  #destpartentfullpath = dsttd.getfullpathbyid(srcitemparentfullpath)
                  destpartentid = dsttd.GetIdByFullPath(srcitemparentfullpath)

              srctd.copyfile(id, destpartentid)pyharm







    #dryrun




# ========= FUNCTIONS


def ModTimeStamp(time):
    # input example : 2018-10-02T14:20:38.496Z
    timestamp = time.replace('T', ' ')
    timestamp = timestamp.replace('Z', '')

    # time : 2018-10-02 14:20:38.496
    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')

    return timestamp


def readcsvfile(filename):
    a = []
    with open(filename) as csvDataFile:
        csvReader = csv.reader(csvDataFile)
        print('in functie')
        for row in csvReader:
            a.append(row)
            # print(row)
    return a


# =============  START MAIN  =====================================================
def main():
    # config logging to console and file
    # logging.debug('This is a debug message')
    # logging.info('This is an info message')
    # logging.warning('This is a warning message')
    # logging.error('This is an error message')
    # logging.critical('This is a critical message')

    logger = logging.getLogger(__name__)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('file.log')
    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    logger.warning('starting log: This is a warning')
    logger.error('starting log: This is an error')

    # === Read teamdrive properties and items
    TdMasterSO = TeamDrive('MASTER-SO')
    # TdMasterSO = TeamDrive('ICT-TECH')
    TdLeraarsSO = TeamDrive('LERAARS-SO')
    # TdLlnbSO = teamdrive('LLNB-SO')

    TdMasterSO.PrintItemList()

    synclog=actionlog()
    #in mapje001
    synclog.add_copyfile(TdMasterSO,'1H3keOI-FkPpTumpSP7ZJPI0rzD2EeAFsWlZxTHVVx64',TdLeraarsSO)
    #in rootfolder
    synclog.add_copyfile(TdMasterSO,'1QX03Iaxj5X0f6SFFl8JSFJ5TzsaFENufF9OmpBNqfFM',TdLeraarsSO)

    synclog.add_deletefile(TdLeraarsSO,'1QX03Iaxj5X0f6SFFl8JSFJ5TzsaFENufF9OmpBNqfFM')
    synclog.add_makedir(TdLeraarsSO, ['002 MAPJE21', '002.1', '002.1.1'])
    synclog.add_deletedir(TdLeraarsSO,['002 MAPJE21', '002.1', '002.1.1'])

    synclog.process()



    # print('Show folders')

    # TdMasterSO.PrintItemList()
    # lijst=TdMasterSO.getfoldercontent('0AJ1PGzg7eU1fUk9PVA','folder')
    # print(lijst)

    # print('subtreelist:')
    #TdMasterSO.GetFolderTreeContent('0AKw5HUdL5Qa_Uk9PVA', 'all')

    # print(TdMasterSO.GetParentNameTreeById('1eCUXs9T_4mzipISx05GHuZbqE6Cxbq04'))
    # print(TdMasterSO.GetParentTreeById('1E0kjqVGgn--Ofj1LFTTpO5t2myPGPoJebYFqytu0oTw'))

    # TdLeraarsSO.deletefolder('10h1buFcMWmgChg4VO_Z3LvtTm06ZQ2gC') #in root
    # TdLeraarsSO.deletefolder('1bpGXQbsRgtpYUQqGFTshJ33S3lbkIoV3') #in 001 MAPJE1
    # 1ZpcamARWtMg0puYZ-oWQiIjn_lirifEs3xAYCz6Q4rY

    # google
    # TdMasterSO.uploadfile('naam',TdLeraarsSO.id)

    #TdMasterSO.copyfile('1ZpcamARWtMg0puYZ-oWQiIjn_lirifEs3xAYCz6Q4rY', TdLeraarsSO.id)
    # TdMasterSO.copyfile('1ZpcamARWtMg0puYZ-oWQiIjn_lirifEs3xAYCz6Q4rY','1JSFcwRpA5H9idb0tMHl_fFXiQpVMSfhT')

    # pdf
    #TdMasterSO.copyfile('1qxmddPda7PQALL_fDdzygZlpww-xoepI',TdLeraarsSO.id)
    #TdMasterSO.copyfile('1B_8xgo3YhylXskNBILOR-PQq-XOAhUQJ','1JSFcwRpA5H9idb0tMHl_fFXiQpVMSfhT')

    #TdMasterSO.createfolderwithparents(['005 MAPJE5', '005.1', '005.1.1'])
    #TdMasterSO.deletefolderwithparents(['005 MAPJE5', '005.1', '005.1.1'])

    #TdMasterSO.deletefolderwithchilderen(['004 MAPJE4'])

    #pair1 = folderpair('003 MAPJE3', TdMasterSO, TdLeraarsSO)
    #pair1.syncfolders()




'''
# === LEES CONFIG BESTANDEN IN
    ArrFolderPairs = readcsvfile('folderpairs.csv')
#  ========  Start met het doorlopen van de folderpairs

    for i in range(0, len(ArrFolderPairs)):
        FolderName = ArrFolderPairs[i][0]
        SourceFolder = 'MASTER-SO'
        DestinationFolder = ArrFolderPairs[i][1]

        #print(ArrFolderPairs[i][0] + ',' + ArrFolderPairs[i][1])

        CurrentPair = folderpair(ArrFolderPairs[i][0],ArrFolderPairs[i][1])
        CurrentPair.print()
'''

if __name__ == '__main__':
    main()

'''

0. Recursive Running through folders
    
  Walk-functie die de inhoud van 1 map (folders en files) inleest in een folder en een files dict
  
  lus:
  voor elke folder in folderdict
    walkfolder
  
def collect_folders(start, depth=-1)
    """ negative depths means unlimited recursion """
    folder_ids = []

    # recursive function that collects all the ids in `acc`
    def recurse(current, depth):
        folder_ids.append(current.id)
        if depth != 0:
            for folder in getChildFolders(current.id):
                # recursive call for each subfolder
                recurse(folder, depth-1)

    recurse(start, depth) # starts the recursion
    return folder_ids

OR
def get_children_folders(self,mother_folder):
    
    #For a given mother folder, returns all children, grand children
    #(and soon) folders of this mother folder.
    
    folders_list=[]
    folders_list.append(mother_folder)
    for folder in folders_list:
        if folder not in folders_list: folders_list.append(folder)
        new_children = getChildFolders(folder.id)
        for child in new_children:
            if child not in folders_list: folders_list.append(child)
    return folders_list


1. SYNC FOLDERS
SRC
- haal parents uit src map en bewaar in FolderPairdict, begin bij srcmap
- koppel id's aan srcmap en parents
- als een (parent)map niet bestaat ->> logerror en stop

DST
- zoek namen mappen in dst en bewaar ID's in extra kolom dict. begin bovenaan
- als een map niet bestaat in dst : maak ze aan en bewaar ID in dict : method createfolder


VERWIJDER SUBMAPPEN die bestaan in DST en niet in SRC

SYNC bestanden in folderpaur en submappen
  overloop SRC mappen en vgl files
    bestaat in beide en lastmodified is gelijk -> skip
    bestaat in beide en lastmodified src > dest -> copy (del + copy?)
    bestaat niet in dest -> copy
    
  overloop DST mappen 
    bestaat in dst maar niet in src : verwijder uit dst   
    




'''

'''


1. lijst  map op MASTER-SO -> LEERKRACHT-SO, LLNB-SO, ... (aanmaken map op zelfde niveau dus ook automatische parent mappen aanmaken
    1. BLABLA, LEERKRACHT-SO
    3.2.5 verlslagen; LEERKRACHT-SO
    3.2.5 verslagen; LLNB-SO

2. voorzien functie 'Exclude' om bepaalde submappen uit te sluiten

3. doorloop lijst

    maak eerst alle mappen aan (incl submappen)

    dan per map : query bestanden op ParentID van sourcemap en sync de bestanden
        - controleer 'last modified'/'creationTime' v/e bestand in souce/dest -> indien gelijk: negeer
        - is lastmodified van source recenter dan dest -> update
        - Eventueel : wat als als modified dest recenter is dan source???? -> copy met timestamp naar master?


=============================================================================================

MASTER-SO                                       SLAVE-SO
naam - ID - Parent - mimeType - lastmodified     naam - ID - Parent - mimeType - lastmodified
naam - ID - Parent - mimeType - lastmodified     naam - ID - Parent - mimeType - lastmodified
naam - ID - Parent - mimeType - lastmodified     naam - ID - Parent - mimeType - lastmodified
naam - ID - Parent - mimeType - lastmodified     naam - ID - Parent - mimeType - lastmodified


Unieke ZoekKey voor vergelijkingen = naam

mappen en documenten zijn items

Logging : functie om acties en resultaten te loggen 


1. lijst met map-paren inlezen in array Arr-FolderPairs (tekstbestand op server)?
    - begin lijst met TeamDrives die ingelezen moeten worden. Hierop gebaseerd inlezen Arrays in stap 2

2. lijst MASTER-SO & lijst ANDERE-SO opvragen en in array bewaren : Vb: ArrMasterSO, ArrLeerkrachtSO, ...
-> opvangen grote lijsten ...




3. vergelijken lijsten
    1e mappen zodat parents van bestanden goed ingesteld kunnen worden
        ArrParents opbouwen : Naam item - ID op SLAVE-SO

    2e documenten synchroniseren


4. ArrActie opbouwen

    bouw tijdens chroniseren een Array op met uit te voeren acties, bewaar deze acties in een tekstbestand voor latere;

    - controleer op nieuwe en bestaande en up te daten  items :
        controleer elk item in ArrMaster :
            -  bestaat in MASTER en SLAVE
                - lastmodified gelijk : niets doen
                - lastmodified in MASTER recenter dan in SLAVE : actie update (= verwijder bestand in slave en copy niewe versie)
            -  bestaat in MASTER en niet in SLAVE : actie : copy van master naar slave
    - controleer op verwijderde items
        - controleer elk item in ArrSlave
            - bestaat item niet in Master : verwijder in slave


5. Wijzigingen doorvoeren
    - doorloop ArrActies en voer wijzigingen door
    - standaard weiger acties / alert als het aantal wijzigingen een drempelwaarde overschrijdt





#==== VOORBEELDCODE

   # master-so='0AKw5HUdL5Qa_Uk9PVA'
   #ict-tech='0AJ1PGzg7eU1fUk9PVA'

    results = drive_service.files().list(
       corpora='teamDrive',
       # corpora='allTeamDrives',
       # q="name contains 'IMG'",
       q="mimeType='application/vnd.google-apps.folder' and trashed = False",
       #q="trashed = False",  #ok
       #q="parents='0AJ1PGzg7eU1fUk9PVA' and trashed = False",
       pageSize=1000,
       teamDriveId='0AJ1PGzg7eU1fUk9PVA',
       supportsTeamDrives=True,
       includeTeamDriveItems=True,
       # useDomainAdminAccess=True,
       fields="files(id, name, parents, mimeType)").execute()
       #fields = "nextPageToken, files(id, name, parents)").execute()

    ArrFoldersMasterSO= results.get('files', [])

    if not ArrFoldersMasterSO:
       print('No files found.')
    else:
       i=0
       print('Files in master_so:')
       #print (ArrFoldersMasterSO)

       for folder in ArrFoldersMasterSO:
          #print(folder['parents'])

          if '0AJ1PGzg7eU1fUk9PVA' in folder['id']:
            print(u'{0} ({1}) ({2}) ({3})'.format(folder['name'], folder['id'], folder['parents'], folder['mimeType']))

          if '0AJ1PGzg7eU1fUk9PVA' in folder['parents']:
            print(u'{0} ({1}) ({2}) ({3})'.format(folder['name'], folder['id'], folder['parents'], folder['mimeType']))
          i=i+1
    print(i)

'''
