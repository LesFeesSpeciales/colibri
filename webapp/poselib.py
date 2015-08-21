# -*- coding: utf8 -*-
# !/usr/bin/python

import os
import glob
import json 

import tornado.ioloop
import tornado.web
import log as rcLog

import base64

libraryPath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'static/content')

debug = True
port = 2048

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


class MainHandler(tornado.web.RequestHandler):

    def get(self, library='/'):
        # self.write('Welcome to Ricochet<br/><br/> <a href="/Shot/">Liste
        #    des shots</a> / <a href="/Asset/">Liste des Assets</a> /
        # <a href="/create/">Creer un element</a>')
        data = {}
        
        data['libs'] = getLibs()
        data['library'] =  "/%s" % library if library else "/"
        data['poses'] = getLibrary(library)
        print data
        self.render('Accueil.html', data=data)
        # self.write("HelloWorld")

class EditHandler(tornado.web.RequestHandler):

    def get(self, pose):

        data = {}
        data['libs'] = getLibs()
        data['library'] =  "/%s" % pose.split('/')[0] if pose else "/"

        if pose.endswith("NEW"):
            data['newPose'] = True
            newId = -1
            gotId = False
            while gotId is False:
                newId += 1
                if not os.path.exists(os.path.join(libraryPath, "%s/%i.json" % (data['library'], newId) )):
                    gotId = True

            data['pose'] = newPose(data['library'], "%s/%i" % (data['library'], newId))

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

class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/edit/(.*)', EditHandler),
            (r'/(.*)', MainHandler),

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

    app = Application()
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()
