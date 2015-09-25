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


import colibri_functions
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
    def get(self, library=0):
        if not library:  # just /lib ->shot root
            ibrary = 0

        pdb = colibri_functions.poseDb()

        if library.endswith("NEWPOSE"):
            # A new pose is created then redirect to its edit
            lib_id = int(library.split('/')[0])
            pose_id = pdb.createPose(title="unnamed pose",
                                     json="",
                                     tags=[],
                                     source_file="",
                                     source_armature="",
                                     lib_id=lib_id)
            self.redirect('/pose/%i' % pose_id)
        else:
            # list the poses of that library
            data = {'libs': pdb.getLibs(),
                    'library': int(library),
                    'tags': pdb.getTags(),
                    'poses': None,
                    }
            if library and library.isdigit():
                data['poses'] = pdb.getPoses(lib_id=int(library))
            self.render("Accueil.html", data=data)

class PosesGetPoseHandler(tornado.web.RequestHandler):
    def get(self, pose):
        pdb = colibri_functions.poseDb()
        pose = pdb.getPoses(pose_id=int(pose))[int(pose)]

        self.write(base64.b64encode(pose['json']))

class PosesEditHandler(tornado.web.RequestHandler):
    def get(self, pose):
        self.write("HelloWorld")

        pdb = colibri_functions.poseDb()
        data = {'libs': pdb.getLibs(),
                'library':0,
                'tags': pdb.getTags(),
                }
        if pose and pose.isdigit():
            data['pose'] = pdb.getPoses(pose_id=int(pose))[int(pose)]
            data['library'] = data['pose']['lib_id']
        self.render("Edit.html", data=data)

    def post(self, pose):
        field = self.get_argument("field", None)
        source_file = self.get_argument("source_file", None)
        pose_id = int(pose)

        pdb = colibri_functions.poseDb()

        if field == "thumbnail":
            print "Hello"
            imgDecode = base64.b64decode(self.request.files['file'][0]['body'])
            print "./static/content/%s.png" % pose
            f = open("./static/content/%s.png" % pose, 'w')
            f.write(imgDecode)
            f.close()

            # Update path
            pdb.updatePose(pose_id,source_file=source_file)
        elif field == 'json_fromBlender':
            json = self.get_argument("json")
            pdb.updatePose(pose_id,json=json, source_file=source_file)
        else:
            print "pose update :", pose, field, self.get_argument("val", None)

            title = self.get_argument("val", None) if field == 'title' else None
            json = self.get_argument("val", None) if field == 'json' else None
            lib_id = self.get_argument("val", None) if field == 'lib_id' else None
            

            # Db connection
            
            # update
            pdb.updatePose(pose_id,
                           title=title,
                           json=json,
                           lib_id=lib_id)

        self.write('OK')


class PosesEditHandlerOld(tornado.web.RequestHandler):
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
            (r'/pose/(.*)/getposeb64/', PosesGetPoseHandler),
            (r'/pose/(.*)', PosesEditHandler),
            (r'/lib/(.*)', MainPosesHandler),

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
    
    #db_initialize(force=True)
    # Else initialize it

    app = Application()
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()
