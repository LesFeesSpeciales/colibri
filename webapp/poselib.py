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

def db_connect(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    return conn, c

def db_initialize(path= dbPath, force=False):
    if os.path.exists(path) and not force:
        print("ERROR : CAN'T INITIALIZE DB : Already existing")
        return
    if os.path.exists(path):
        os.remove(path)

    conn, c = db_connect(path)

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
    # Poses to lib table (1to1)
    c.execute("CREATE TABLE pose_2_lib(pose_id INT, lib_id INT)")

    conn.commit()

    createPose(conn, c, "test Title", "hahf", ["mains", "poiraux", "jean michel", "mains"], "titi", "toto")
    conn.close()
# TAGS


def createTag(conn, c, tag_name):
    '''create a tag and returns its id. 
    if the tag exists, return it's id'''

    c.execute("SELECT tag_id FROM tags WHERE tag_name = '%s'" % tag_name)
    r = c.fetchone()
    if not r:
        c.execute("INSERT INTO tags ('tag_name') VALUES('%s')" % tag_name)
        c.execute("SELECT tag_id FROM tags WHERE  tag_id = (SELECT MAX(tag_id)  FROM tags);")
        tag_id = c.fetchone()[0]
    else:
        tag_id = r[0]
    conn.commit()
    return tag_id


def addTagToPose(conn, c, tag_name, pose_id):
    tag_id = createTag(conn, c, tag_name)
    c.execute("SELECT * from tags_2_poses WHERE tag_id = %i and pose_id = %i" % (tag_id, pose_id))
    if c.fetchone():
        # Tag already assigned to pose
        return
    else:
        c.execute("INSERT INTO tags_2_poses VALUES(%i, %i)" % (tag_id, pose_id))
        conn.commit()

def deleteTagToPose(conn, c, tag_name, pose_id):
    pass

def deleteTag(conn, c, tag_name):
    pass

def getTags():
    pass

# POSES

def createPose(conn, c, title, json, tags=[], source_file="", source_armature=""):
    c.execute("INSERT INTO poses(title, json, creation_date, update_date, source_file, source_armature) VALUES(\
                '%s', '%s', %i, %i, '%s', '%s')" %
                (title, base64.b64encode(json), int(time.time()), int(time.time()), source_file, source_armature))
    
    c.execute("SELECT * FROM poses WHERE  pose_id = (SELECT MAX(pose_id)  FROM poses);")
    pose_id = c.fetchone()[0]


    for tag in tags:
        addTagToPose(conn, c, tag, pose_id)
    conn.commit()
    return pose_id

def updatePose(conn, c, title=None, json=None, tags=None, source_file=None, source_armature=None):
    pass

def deletePose(conn, c, pose_id):
    # Delete tag relations
    # Delete lib relations
    # Delete pose
    pass

def getPoses(conn, c):
    pass

# Libs

def addLib():
    pass

def updateLib():
    pass

def deleteLib(deleteContent=False, transferTo=None):
    pass

def getLibs():
    c.execute("SELECT lib_id, lib_name, lib_parent from librairies ORDER BY lib_parent")
    _libs = {}
    librairies = {0:{'lib_name':'/', 'children':{}}}
    for r in c.fetchall():
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
    db_initialize(force=True)
    # Else initialize it

    app = Application()
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()
