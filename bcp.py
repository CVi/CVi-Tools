#!/usr/bin/python
import sys
import os
import datetime
from optparse import OptionParser
from optparse import OptionGroup
import pprint
import pickle

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText 
from email.Utils import COMMASPACE, formatdate
from email import Encoders


def DoubleInit():
  print "Allready initialized"
def ListDB():
  print "Listing Databases"

def SendWMail(send_to, subject, files=[]):
  assert type(send_to)==str
  assert type(files)==list
  assert config.sender

  msg = MIMEMultipart()
  msg['From'] = config.sender
  msg['To'] = send_to
  msg['Date'] = formatdate(localtime=True)
  msg['Subject'] = subject
  msg.attach( MIMEText("Backup attached") )
  for f in files:
    part = MIMEBase('application', "octet-stream")
    part.set_payload( open(f,"rb").read() )
    Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
    msg.attach(part)
  smtp = smtplib.SMTP('localhost')
  smtp.sendmail(config.sender, send_to, msg.as_string())
  smtp.close()

def DumpDBnMail(db):
  data = { 'database':db.database, 'server':db.server, 'user':db.username, 'pass':db.password }
  execode  = "rm -rf ./tmp/* &&"
  execode += "mysqldump \"%(database)s\" --add-drop-table -c -h \"%(server)s\" -u \"%(user)s\" -p\"%(pass)s\" "
  execode += " | gzip | split - \"./tmp/%(database)s.sql.gz.\" -b 5242880"
  execode = execode % data
  os.system(execode)
  files = os.listdir("./tmp/")
  files_num = len(files)
  file_number = 1
  dtf = datetime.date.today() 
  dtf = dtf.isoformat()
  for f in files:
    item = ["./tmp/%s" % f]
    pprint.pprint(item)
    subject = "Backup of database %s file %i of %i for %s" % (db.database, file_number, files_num, dtf )
    SendWMail(config.email, subject, item) 

def run_cron():
  if not config.isusable():
    print "Not all required settings are set in configuration"
    sys.exit()
  for db in config.databases:
    if db.isusable():
      if config.runs.get(db.database) != datetime.date.today():
        DumpDBnMail(db)
        run = { db.database: datetime.date.today()}
        config.runs.update(run)
      else:
        print "%s has been backed up today" % db.database
    else:
      print "Database %s does not have enugh config to backup" % db.database
  RunsStore(config)

def EditDB():
  if len(args) < 3:
    ListDB()
    sys.exit()
  dbid = int(args[2])
  db = config.databases[dbid]
  if options.database:
    db.database = options.database
  if options.type:
    db.type = options.type
  if options.server:
    db.server = options.server
  if options.username:
    db.username = options.username
  if options.password:
    db.password = options.password
  ConfigStore(config)
  OutputConfig()
  sys.exit()


def AddDB():
  db = ConfigDatabase()
  if options.database:
    db.database = options.database
  if options.type:
    db.type = options.type
  if options.server:
    db.server = options.server
  if options.username:
    db.username = options.username
  if options.password:
    db.password = options.password
  config.databases.append(db)
  ConfigStore(config)
  OutputConfig()
  sys.exit()

def ConfEdit():
  if options.email:
    print "updating email from %s to %s" % (config.email, options.email)
    config.email = options.email
  if options.sender:
    print "Updating sender mail from %s to %s" % (config.sender, options.sender)
    config.sender = options.sender
  ConfigStore(config)
  OutputConfig()
  sys.exit()

def OutputConfig():
  print ""
  print "Current Configuration:"
  print "  Main Configuration:"
  print "    Email Address: %s" % config.email
  print "    Sender email: %s" % config.sender
  for database in config.databases[:]:
    k = config.databases.index(database)
    print "  Database %i" % k
    print "    Name: %s" % database.database
    print "    Type: %s" % database.type
    print "    Server: %s" % database.server
    print "    Username: %s" % database.username
    if database.password:
      print "    Password length %i" % len(database.password)
    else:
      print "    No Password Set"
    if database.isusable():
      print "    Enugh information input"
    else:
      print "    Not enugh information input"
 
def DatabaseEdit():
  print "Database"
  dboptions = {
    "list":ListDB,
    "add":AddDB,
    "edit":EditDB
  }
  if len(args) < 2:
    ListDBOpts()
  else:
    dboptions.get(args[1], ListDBOpts)()

def ListDBOpts():
  print "%s database add [opts]             - Adds a database to configuration" % command
  print "%s database list                   - Lists all configured databases" % command
  print "%s database edit (database) [opts] - Edits a database" % command

def ConfInit():
  config = Config()
  if options.email:
    print "Email address was supplied, using %s" % options.email
    config.email = options.email
  else:
    print "No email address supplied"
  ConfigStore(config)
  sys.exit()

def ConfigStore(config):
  conf_file = open('config.pkl', 'wb')
  db_file = open('db.pcl', 'wb')
  runs_file = open('runs.pcl', 'wb')
  pickle.dump(config,conf_file)
  pickle.dump(config.databases, db_file)
  pickle.dump(config.runs, runs_file)
  conf_file.close()
  db_file.close()
  runs_file.close()

def RunsStore(config):
  runs_file = open('runs.pcl', 'wb')
  pickle.dump(config.runs, runs_file)
  runs_file.close()

def ConfigLoad():
  dbs_avail = True
  runs_avail = True
  try:
    conf_file = open('config.pkl', 'rb')
  except IOError:
    return False
  try: 
    db_file = open('db.pcl', 'rb')
  except IOError:
    dbs_avail = False
  try:
    runs_file = open('runs.pcl', 'rb')
  except IOError:
    runs_avail = False
  config = pickle.load(conf_file)
  conf_file.close()
  if dbs_avail:
    config.databases = pickle.load(db_file)
    db_file.close()
  if runs_avail:
    config.runs = pickle.load(runs_file)
    runs_file.close()
  return config

class Config:
  __name__ = "BacScriptConf"
  email = False
  sender = False
  databases = []
  runs = {}
  def __call__():
    pass
  def isusable(self):
    if not self.email:
      return False
    elif not self.sender:
      return False
    else:
      return True

class ConfigDatabase:
  __name__ = "BacScriptConfDB"
  server = False
  type = "mysql"
  username = False
  password = False
  database = False
  def __call__():
    pass
  def isusable(self):
    if not self.server:
      return False
    elif not self.username:
      return False
    elif not self.database:
      return False
    else:
      return True

usage  = "usage: %prog \n"
usage += " or:   %prog [options] init\n"
usage += " or:   %prog [options] database\n"
usage += " or:   %prog [options] conf\n"

parser = OptionParser(usage=usage)
dbopts = OptionGroup(parser, "Database options", "options used in conjunction with the 'database' argument.")

#parser.add_option("-a", "--all", action="store_true", dest="show_all", default=False, help="Shows all options, included advanced ones")
parser.add_option("-m", "--email", action="store", type="string", default=False, dest="email")
parser.add_option("-f", "--sender", action="store", type="string", default=False, dest="sender")

dbopts.add_option("-d", "--database", action="store", type="string", default=False, dest="database", help="Used in conjunction with 'add' or 'edit' to set the database name")
dbopts.add_option("-s", "--server", action="store", type="string", default=False, dest="server", help="Used in conjunction with 'add' or 'edit' to set database server")
dbopts.add_option("-u", "--username", action="store", type="string", default=False, dest="username", help="Used in conjunction with 'add' or 'edit' to set database username")
dbopts.add_option("-p", "--password", action="store", type="string", default=False, dest="password", help="Used in conjunction with 'add' or 'edit' to set database password")
dbopts.add_option("-t", "--type", action="store", type="string", default=False, dest="type", help="Used in conjunction with 'add' or 'edit' to set database type")


parser.add_option_group(dbopts)

(options, args) = parser.parse_args()

values = {
  "database": DatabaseEdit,
  "conf": ConfEdit,
  "init": DoubleInit,
}

command = sys.argv[0]

config = ConfigLoad()
if not config:
  if len(args) > 0 and args[0] == "init":
    ConfInit() 
  else:
    print "not initialized"
    sys.exit() 
if len(args) < 1:
  run_cron()
else:
  values.get(args[0], run_cron)()
