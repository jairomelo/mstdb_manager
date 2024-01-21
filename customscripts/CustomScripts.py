
from grp import getgrnam
import os
from pwd import getpwnam

class FileManager:
    
    def createLogsFiles(self, filename, logdir):
        os.makedirs(logdir, exist_ok=True)
        newLogFile = os.path.join(logdir, filename)

        if not os.path.isfile(newLogFile):
            open(newLogFile, 'w')

            uid = getpwnam('www-data').pw_uid
            gid = getgrnam('www-data').gr_gid

            os.chown(newLogFile, uid, gid)
            os.chmod(newLogFile, 755)