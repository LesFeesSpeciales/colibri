
import sqlite3
import time
import base64
import re
import os

dbPath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'colibri.sqlite')
debug = True
port = 2048

version = "Alpha 1.0"
dbVersion = 1 # db version should change only if structure changes


def escape(i):
    return re.escape(i)

class poseDb:
    def __init__(self, path=dbPath):
        self.path = path
        self.conn = None
        self.c = None

        
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
        self.db_disconnect()

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
        self.addLib('SHARED', 0)
        self.addLib('PRIVATE', 0)

        c.execute("CREATE TABLE pose_2_lib(pose_id INT, lib_id INT)")

        conn.commit()

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
        return [  [str tag_name, int tag_id, int tag number of uses, float use factor from 1 (0%) to 2(100%)], ... ]
        default order is by name or by count if specified
        '''
        self.c.execute("SELECT COUNT(*) FROM tags_2_poses")
        totalAssignedTags = self.c.fetchone()[0]
        cmd = "SELECT tags.tag_id, tags.tag_name, tmpJoin.resultat FROM tags\
              LEFT JOIN (select tags_2_poses.tag_id,\
                                count(DISTINCT tags_2_poses.pose_id) as resultat\
                                from tags_2_poses GROUP BY tags_2_poses.tag_id\
                        ) AS tmpJoin ON tags.tag_id = tmpJoin.tag_id"
        self.c.execute(cmd)
        tags = []
        for r in self.c.fetchall():
            tags.append((r[0], r[1], r[2], 1+((totalAssignedTags/r[2])/100.0)))
        
        if orderByCount:
            tags.sort(key= lambda x: x[2])
            tags.reverse()
        else:
            tags.sort(key= lambda x: x[1].upper())
        return tags

    # POSES

    def createPose(self, title, json, tags=[], source_file="", source_armature="", lib_id=0):
        '''
        Providing the basic infos, it create a new pose in the database
        '''
        self.c.execute("INSERT INTO poses(title, json, creation_date, update_date, source_file, source_armature) VALUES(\
                    ?, ?, ?, ?, ?, ?)",
                    (title, base64.b64encode(json), int(time.time()), int(time.time()), source_file, source_armature))
        
        self.c.execute("SELECT * FROM poses WHERE  pose_id = (SELECT MAX(pose_id)  FROM poses);")
        pose_id = self.c.fetchone()[0]

        
        self.c.execute("INSERT INTO pose_2_lib VALUES(?, ?)" , (pose_id, lib_id))
        
        
        for tag in tags:
            self.addTagToPose(tag, pose_id)
        self.conn.commit()
        return pose_id
    def countAsApplied(self, pose_id):
        pose_id = int(pose_id)
        cmd = 'UPDATE poses SET count = (SELECT count FROM poses WHERE pose_id = %i)+1 where pose_id = %i' % (pose_id, pose_id)
        print cmd
        self.c.execute(cmd)
        self.conn.commit()

    def updatePose(self, pose_id, title=None, json=None, tags=None, source_file=None, source_armature=None, lib_id = None):
        '''
        provided a pose_id it will update all the other provided fields
        '''

        pose_id = int(pose_id)

        updatedKeys = []
        updatedValues = []
        if title:
            updatedKeys.append("title")
            updatedValues.append(title)
        if json:
            updatedKeys.append("json")
            updatedValues.append(base64.b64encode(json))
        if source_file:
            updatedKeys.append("source_file")
            updatedValues.append(source_file)
        if source_armature:
            updatedKeys.append("source_armature")
            updatedValues.append(source_armature)

        if updatedKeys:
            updatedKeys.append('update_date')
            updatedValues.append(int(time.time()))

            cmd = 'UPDATE poses SET '
            cmd += " = ?, ".join(updatedKeys)
            cmd += " = ? WHERE pose_id = %i" % pose_id

            print cmd, updatedValues
            self.c.execute(cmd, updatedValues)
            self.conn.commit()

        if lib_id:
            cmd = 'UPDATE pose_2_lib SET lib_id = %i where pose_id = %i' % (int(lib_id), pose_id)
            print cmd
            self.c.execute(cmd)
            self.conn.commit()
        if tags:
            pass
        pass

    def deletePose(self, pose_id):
        '''
        Delete a pose, the lib relations and tags relations
        '''
        # Delete tag relations
        # Delete lib relations
        # Delete pose
        pass

    def getPoses(self, pose_id=None, lib_id=None):
        '''
        get the list of all poses in a provided lib
        '''
        cmd = "SELECT poses.pose_id, poses.title, poses.json,\
                                poses.thumbnail_path, poses.count, poses.creation_date,\
                                poses.update_date, poses.source_file, poses.source_armature,\
                                tags.tag_id, tags.tag_name\
                                from poses \
                                LEFT JOIN tags_2_poses ON poses.pose_id = tags_2_poses.pose_id\
                                LEFT JOIN tags ON tags_2_poses.tag_id = tags.tag_id"
        if lib_id:
            cmd += " WHERE poses.pose_id in (SELECT pose_id FROM pose_2_lib WHERE lib_id = ?)"
            arg1 = lib_id
        elif pose_id:
            cmd += " WHERE poses.pose_id = ?"
            arg1 = pose_id
        else:
            print "ERROR, lib_id or pose_id not provided"
            return None
        self.c.execute(cmd, [arg1])
        poses = {}
        # orderByTitle = []
        # orderByCount = []

        for r in self.c.fetchall():
            if not r[0] in poses:
                self.c.execute('SELECT lib_id from pose_2_lib WHERE pose_id = ?', [r[0]])  # To include in the query before 
                lib_id = self.c.fetchone()[0]
                poses[r[0]] = {
                    'pose_id': r[0],
                    'title': r[1],
                    'lib_id': lib_id,
                    'json': base64.b64decode(r[2]),
                    'thumbnail_path': r[3],
                    'count': r[4],
                    'creation_date': r[5],
                    'creation_date-h': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[5])),
                    'update_date': r[6],
                    'update_date-h': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[6])),
                    'source_file': r[7],
                    'source_armature': r[8],
                    'tags': [],
                    #'library': (r[11], r[12])
                }
                # orderByTitle.append((r[1], r[0]))
                # orderByCount.append((r[4], r[0]))
            poses[r[0]]['tags'].append((r[10], r[9]))
        # orderByTitle.sort()
        # orderByCount.sort()
        # poses["_ORDER"] = {'title':orderByTitle, 'count':orderByCount}
        print poses
        return poses

    # Libs

    def addLib(self, lib_name, lib_parent=0, lib_type="poses"):
        '''
        add a new library folder
        '''
        self.c.execute("INSERT INTO libraries(lib_name, lib_parent, lib_type) VALUES( ?, ?, ?)", (lib_name, lib_parent, lib_type))
        
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
        self.c.execute("SELECT lib_id, lib_name, lib_parent from libraries ORDER BY lib_parent, lib_name")
        libraries = {0:{'lib_name':'/', 'lib_parent':None, 'path': ''}, "_ORDER":[0]}

        for r in self.c.fetchall():
            '''
            This part helps to display and order the list of libs
            '''
            parent = r[2]
            path = ""
            while parent:
                if not parent in libraries:
                    parent = 0
                else:
                    path +=  "--"
                    parent = libraries[parent]['lib_parent']
            path += r[1]
            libraries[r[0]] = {'lib_name':r[1], 'lib_parent':r[2], 'path': path}
            libraries['_ORDER'].insert(libraries['_ORDER'].index(r[2])+1, r[0])

        return libraries
        #librairies = {0:{'lib_name':'/', 'children':{}}}
        #for l in _libs:
