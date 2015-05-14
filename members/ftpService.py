import ftplib
from django.conf import settings
from os import path, unlink

HOST = 'ftp.ktconsultants.co.uk'
FILE = 'TransactionData.xls'
USER = 'cwltc@ktconsultants.co.uk'
PASS = 'Cwltc2010$$'

def ftpGet():
    try:
        ftp = ftplib.FTP(HOST)
    except (socket.error, socket.gaierror), e:
        return 'ERROR: cannot reach "%s"' % HOST
        
    try:
        ftp.login(USER,PASS)
    except ftplib.error_perm:
        ftp.quit()
        return 'ERROR: cannot login'
       
    try:
        tPath = path.join(settings.PROJECT_ROOT, FILE)
        tFile = open(tPath, 'wb')
        ftp.retrbinary('RETR %s' % FILE, tFile.write)
    except ftplib.error_perm:
        unlink(FILE)
        return 'ERROR: cannot read file "%s"' % FILE
    
    tFile.close
    ftp.quit()
    return 'OK: File size: "%i"' % path.getsize(tPath)

#def ftpPut():
#    try:
#        ftp = ftplib.FTP(HOST)
#    except (socket.error, socket.gaierror), e:
#        return 'ERROR: cannot reach "%s"' % HOST 
    
#    try:
#        ftp.login(USER,PASS)
#    except ftplib.error_perm:
#        ftp.quit()
#        return 'ERROR: cannot login'

#    try:
#        ftp.sendcmd("TYPE I")
#        tPath = path.join(settings.PROJECT_ROOT, FILE)
#        tFile = open(tPath, 'wb')
#        ftp.retrbinary('RETR %s' % FILE, tFile.write)
#    except ftplib.error_perm:
#        unlink(FILE)
#        return 'ERROR: cannot read file "%s"' % FILE
    
#    ftp.storbinary('STOR %s' % i, open(os.path.join('V://GIS//Maps//County//11x17shd//',i), "rb"))