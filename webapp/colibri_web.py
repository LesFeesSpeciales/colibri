# -*- coding: utf8 -*-
# !/usr/bin/python

import os
import glob  # TO DELETE
import json
import sqlite3
import time

import tornado.ioloop
import tornado.web
import log as rcLog

import base64


"""
TODO

SQLITE edition
- all the data is saved in an sqlite file (except the thumbnails)
    - default path is ./colibri.sqlite
- structure
    - tables :
        * tags : tag_id, tag_name, tag_long_name
        * tags_2_poses : tag_id, pose_id (many to many)
        * poses : pose_id, pose_title, pose_json, creation_date, thumbnail_path
                  applied_counter
        * librairies : lib_id, lib_name, lib_parent, lib_type
        * pose_2_lib : pose_id, lib_id (1 to 1)
        * config : meta_name, meta_value (version, date, ...)
    - images stored in ./static/content/poses/pose_id.png
Filtering options
    - filtering on name or tags
    - filtering by most used (applied_counter)
    - filtering by bones ! (from a blender selection : filter all poses
        that include those bones (or/and))
    - filtering by armature


Remake the preview page with all the thumbnails
    - hability to change size
    - option to append the pose from that page

Subfolders :
    - create as much subfolders as you want
    - Tree hierarchy

From the pose
- Apply invert pose (for hands for example)
- Select affected bones (whithout applying)
- Find and replace (for prefix switch)
- Bones matching (match bones for ones present in the scene)
    Need 2 directions com
- Bones matching pressets (saves the matches)

shared lib and private libs

"""


libraryPath = os.path.join(  # TO DELETE
    os.path.dirname(os.path.realpath(__file__)),
    'static/content')

dbPath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'colibri.sqlite')
debug = True
port = 2048

version = "Alpha 1.0"
dbVersion = 1 # db version should change only if structure changes

##################################
#        SQLITE FUNCTIONS        #
##################################


class poseDb:
    def __init__(self, path=dbPath):
        self.path = path
        self.conn = None
        self.c = None

        self.db_initialize(force=True)
        self.db_connect()

    def db_connect(self):
        '''
        Connect to the sqlite db
        '''
        self.conn = sqlite3.connect(self.path)
        self.c = self.conn.cursor()

    def db_disconnect(self):
        '''
        Close the connection to the sqlite db
        '''
        self.conn.close()

    def db_initialize(self, force=False):
        '''
        This function initialize a sqlite database with the right tables in it.
        '''
        if os.path.exists(self.path) and not force:
            print("ERROR : CAN'T INITIALIZE DB : Already existing")
            return
        if os.path.exists(self.path):
            os.remove(self.path)

        self.db_connect()
        c = self.c
        conn = self.conn

        c.execute('SELECT SQLITE_VERSION()')
        version = c.fetchone()
        print("Initializing sqlite db of version %s" % version)

        # Settings tables, metas and values
        c.execute("CREATE TABLE settings(meta_name TEXT, meta_value TEXT)")
        c.execute("INSERT INTO Settings VALUES('db_version','%i')" % dbVersion)
        c.execute("INSERT INTO Settings VALUES('init_time','%i')" % int(time.time()))

        # Pose table
        c.execute("CREATE TABLE poses(pose_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, json TEXT,\
                   thumbnail_path TEXT, count INT DEFAULT 0, creation_date INT,\
                   update_date INT, source_file TEXT, source_armature TEXT)")
        # Tags table
        c.execute("CREATE TABLE tags(tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag_name TEXT)")
        # Tags to poses table (many to many)
        c.execute("CREATE TABLE tags_2_poses(tag_id INT , pose_id INT)")
        # Library table
        c.execute("CREATE TABLE libraries(lib_id INTEGER PRIMARY KEY AUTOINCREMENT, lib_name TEXT, lib_parent INT,\
                   lib_type TEXT)")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES('SHARED', 0, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES('PRIVATE', 0, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Victor', 1, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Flavio', 2, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Franck', 1, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Hands', 3, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Faces', 3, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Body', 3, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Stand', 8, 'poses')")
        c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( 'Active', 8, 'poses')")
        # Poses to lib table (1to1)
        c.execute("CREATE TABLE pose_2_lib(pose_id INT, lib_id INT)")


        self.createPose("test Title", "hahf", ["mains", "poiraux", "jean michel", "mains"], "titi", "toto")

        conn.commit()

        
        conn.close()
    # TAGS

    def getTagId(self, tag_name):
        self.c.execute("SELECT tag_id FROM tags WHERE tag_name = '%s'" % tag_name)
        r = self.c.fetchone()
        if r:
            return r[0]
        else:
            return None

    def createTag(self, tag_name):
        '''
        create a tag and returns its id. 
        If the tag already exists returns its id
        '''

        tag_id = self.getTagId(tag_name)

        if not tag_id:
            self.c.execute("INSERT INTO tags ('tag_name') VALUES('%s')" % tag_name)
            self.c.execute("SELECT tag_id FROM tags WHERE  tag_id = (SELECT MAX(tag_id)  FROM tags);")
            tag_id = self.c.fetchone()[0]
            self.conn.commit()
        
        return tag_id


    def addTagToPose(self, tag_name, pose_id):
        '''
        Provided a tag (text) and a pose_id, it links them in the db
        If the tag does not exists it will be created
        '''
        tag_id = self.createTag(tag_name)
        self.c.execute("SELECT * from tags_2_poses WHERE tag_id = %i and pose_id = %i" % (tag_id, pose_id))
        if self.c.fetchone():
            # Tag already assigned to pose
            return
        else:
            self.c.execute("INSERT INTO tags_2_poses VALUES(%i, %i)" % (tag_id, pose_id))
            self.conn.commit()

    def deleteTagToPose(self, tag_name, pose_id):
        '''
        delete tag link to a pose if it exists
        '''
        tag_id = self.getTagId(tag_name)
        if tag_id:
            self.c.execute("DELETE FROM tags_2_poses WHERE tag_id = %i and pose_id =%i" % (tag_id, pose_id))
        self.conn.commit()

    def deleteTag(self, tag_name):
        '''
        delete a tag and all the poses linked to it !
        '''
        tag_id = self.getTagId(tag_name)
        if tag_id:
            self.c.execute("DELETE FROM tags_2_poses WHERE tag_id = %i" % (tag_id))
            self.c.execute("DELETE FROM tags WHERE tag_id = %i" % (tag_id))
            self.conn.commit()

    def getTags(self, orderByCount=False):
        '''
        get the list of all the tags and ids
        return [  [tag_name, tag_id], ... ] order by name (default) or by count
        '''
        self.c.execute('SELECT tag_id, tag_name from tags')
        tags = []
        for r in c.fetchall():
            tags.append((r[1], r[0]))

        tags.sort()
        return tags

    # POSES

    def createPose(self, title, json, tags=[], source_file="", source_armature=""):
        '''
        Providing the basic infos, it create a new pose in the database
        '''
        self.c.execute("INSERT INTO poses(title, json, creation_date, update_date, source_file, source_armature) VALUES(\
                    '%s', '%s', %i, %i, '%s', '%s')" %
                    (title, base64.b64encode(json), int(time.time()), int(time.time()), source_file, source_armature))
        
        self.c.execute("SELECT * FROM poses WHERE  pose_id = (SELECT MAX(pose_id)  FROM poses);")
        pose_id = self.c.fetchone()[0]


        for tag in tags:
            self.addTagToPose(tag, pose_id)
        self.conn.commit()
        return pose_id

    def updatePose(self, pose_id, title=None, json=None, tags=None, source_file=None, source_armature=None):
        '''
        provided a pose_id it will update all the other provided fields
        '''
        pass

    def deletePose(self, pose_id):
        '''
        Delete a pose, the lib relations and tags relations
        '''
        # Delete tag relations
        # Delete lib relations
        # Delete pose
        pass

    def getPoses(self):
        '''
        get the list of all poses
        or filter them if ...
        '''
        pass

    # Libs

    def addLib(self):
        '''
        add a new library folder
        '''
        pass

    def updateLib(self):
        '''
        change the name or parent library folder
        '''
        pass

    def deleteLib(self, deleteContent=False, transferTo=None):
        '''
        delete a library folder. Content might be deleted or transfered to another library
        '''
        pass

    def getLibs(self):
        '''
        get the list of available librairies
        '''
        self.c.execute("SELECT lib_id, lib_name, lib_parent from librairies ORDER BY lib_parent")
        _libs = {}
        librairies = {0:{'lib_name':'/', 'children':{}}}
        for r in self.c.fetchall():
            #_libs[r[0]] = {'lib_name':r[1], 'lib_parent':r[2]}

            pass
        #librairies = {0:{'lib_name':'/', 'children':{}}}
        #for l in _libs:

##################################
#        POSES FUNCTIONS         #
##################################


def getPose(p):
    with open(p, 'r+') as file:
        data = json.load(file)
        data['id'] = os.path.basename(p).split('.')[0]

    file.close()
    return data


def savePose(path, data):
    print path
    print data
    f = open(path, "w")
    f.write(json.dumps(data))
    f.close()
    return True


def getLibrary(path='/'):
    libPath = os.path.join(libraryPath, path)
    poses = glob.glob(libPath + "/*.json")
    results = []
    for p in poses:
        results.append(getPose(p))
    return results


def newPose(lib, pose, title="pose title", animated=False, blenderPose="", tags=[]):
    # {"lib": "/victor", "tags": [], "pose": "/victor/2", "title": "Fist 2", "animated": false, "blenderPose": ""}
    return {
        'lib': lib,
        'pose': pose,
        'title': title,
        'animated': animated,
        'blenderPose': blenderPose,
        'tags': tags,
    }


def getLibs():

    libContent = os.listdir(libraryPath)
    libs = ['/']
    for d in libContent:
        if os.path.isdir(os.path.join(libraryPath, d)):
            libs.append('/%s'% d)
    return libs


def makeNewPose(metas, obj=None, thumnail=None):
    pass

##################################
#        POSES HANDLERS          #
##################################


class MainPosesHandler(tornado.web.RequestHandler):

    def get(self, library='/'):
        # self.write('Welcome to Ricochet<br/><br/> <a href="/Shot/">Liste
        #    des shots</a> / <a href="/Asset/">Liste des Assets</a> /
        # <a href="/create/">Creer un element</a>')
        data = {}
        data['libs'] = getLibs()
        data['library'] = "/%s" % library if library else "/"
        data['poses'] = getLibrary(library)
        print data
        self.render('Accueil.html', data=data)
        # self.write("HelloWorld")

class PosesEditHandler(tornado.web.RequestHandler):
    def get(self, pose):

        data = {}
        data['libs'] = getLibs()
        data['library'] = "/%s" % pose.split('/')[0] if pose else "/"

        if pose.endswith("NEW"):
            data['newPose'] = True
            newId = -1
            gotId = False
            while gotId is False:
                newId += 1
                path = os.path.join(libraryPath, ".%s/%i.json" % (data['library'], newId) )
                if not os.path.exists(path):
                    gotId = True

            data['pose'] = newPose(data['library'], "%s/%i" % (data['library'], newId))
            savePose(path, data['pose'])
        else:
            data['newPose'] = False
            data['pose'] = getPose(os.path.join(libraryPath, "%s.json" % pose))

        self.render('edit.html', data=data)

    def post(self, pose):
        # thumbnail provided
        try:
            imgDecode = base64.b64decode(self.request.files['file'][0]['body'])
            f = open("./static/content/%s.png" % pose, 'w')
            f.write(imgDecode)
            f.close()
            self.write("OK")
        except:
            pass

        # get new Json ?
        print 'pose', pose
        lib =  "/%s" % pose.split('/')[0] if pose else "/"
        title = self.get_argument("title", None)
        blenderPose = self.get_argument("blenderPose", None)
        jsonFile = os.path.join(libraryPath, ".%s.json" % (pose))
        print libraryPath, jsonFile
        if os.path.exists(jsonFile):
            # Update
            currentPose = getPose(jsonFile)
            if title:
                currentPose['title'] = title
            if blenderPose:
                currentPose['blenderPose'] = blenderPose

        else:
            currentPose = newPose(lib=lib, pose=pose, title=title, blenderPose=blenderPose)

        # Save currentPose
        # TODO
        savePose(jsonFile, currentPose)
        self.write('OK')


##################################
#        OTHER HANDLERS          #
##################################

##################################
#        APPLICATION INIT        #
##################################

class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/poses/edit/(.*)', PosesEditHandler),
            (r'/poses/(.*)', MainPosesHandler),

        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
        )
        tornado.web.Application.__init__(self, handlers, debug=debug, **settings)

if __name__ == '__main__':
    log = rcLog.getLogger('ricoweb', debug)

    log.info('Starting %s' % __file__)
    log.info('Server running on port %d' % port)
    log.info('Debug level %s' % log.level)

    # Check if sqlite file exists
    pdb = poseDb()
    #db_initialize(force=True)
    # Else initialize it

    app = Application()
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()
