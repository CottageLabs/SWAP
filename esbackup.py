#! /usr/bin/python

from datetime import datetime
import os, requests, json, shutil

# make sure this script is executable, then symlink it from a cron folder,
# or trigger a schedule for it howevr you see fit

# set the location of the elasticsearch server
# if set, queries retrieving every record from every index 
# will be sent, and the JSON results will be saved to file
# do not include trailing slash
location = 'http://localhost:9200'

# size of query results to request per hit on the indices
batchsize = 100

# list the names of any indices and types to ignore
indexignore = ["leaps"]
typeignore = {
    "swap": ["simd"]
}

# specify the directory on the server running this script where
# the index files are stored. If set, they will be copied too.
# do not include trailing slash. this script must run with 
# permissions allowing it to copy this directory, or copying will fail
directory = ''

# set where to save the backup files to
# do not include trailing slash
# folder should exist
backupto = '/home/cloo/BACKUPS/es/SWAP'

# specify how many days to keep backups
# TODO: implement this
deleteafter = 0

# specify whether or not to compress backups
# TODO: implement this
compress = False

# set an email address for activity alerts
# TODO: implement this
mailto = ''

# set a filename to append logs to. this script must run with 
# permissions allowing it to write to this file, or logging will fail
logto = ''

# END OF SETTINGS
# ==============================================================================

# track the actions that are done, for the log
done = []

# create a folder for todays backup, and set todays backup path
time = datetime.now().strftime("%H%M")
today = datetime.now().strftime("%Y%m%d")
done.append('==============================')
done.append(time)
done.append(today)
done.append('backup starting')

# TODO: check if the backup path exists, try to create if necessary, log outcome

# make the backup folder for today
backuppath = backupto + '/' + today + '/'
try:
    os.makedirs(backuppath)
    done.append('backup directory created for today')
except:
    done.append('failed to create backup directory for today')

# make the backup folder for just now
backuppath += time
try:
    os.makedirs(backuppath)
    done.append('backup directory created for ' + time)
except:
    done.append('failed to create back directory for ' + time)

# if a location is set, query every index
if location:
    done.append('performing backups via index query')
    rs = requests.get(location + '/' + '_status')
    indices = rs.json()['indices'].keys()
    for index in indices:
        if index not in indexignore:
            ts = requests.get(location + '/' + index + '/_mapping')
            types = ts.json()[index].keys()
            for t in types:
                if t not in typeignore.get(index,[]):
                    rh = requests.get(location + '/' + index + '/' + t + '/_search?q=*&size=0')
                    size = rh.json()['hits']['total']
                    fro = 0
                    recs = []
                    while fro < size:
                        r = requests.get(location + '/' + index + '/' + t + '/_search?q=*&from=' + str(fro) + '&size=' + str(batchsize))
                        recs = recs + [i['_source'] for i in r.json()['hits']['hits']]
                        fro += batchsize
                    out = open(backuppath + index + '_' + t + '.json', 'w')
                    out.write(json.dumps(recs,indent=4))
                    out.close()
                    done.append(location + '/' + index + '/' + t + " total " + str(size) + " got " + str(len(recs)))

# if told where the index files are stored, grab a copy of them too
if directory:
    try:
        shutil.copytree(directory,backuppath + '/data')
        done.append('performing backup of index files from ' + directory)
    except:
        pass

# remove old backups based on defined rota
if deleteafter:
    pass

# write to the log, if set
if logto:
    try:
        out.open(logto, 'a+')
        out.write('' + json.dumps(done))
        out.close()
    except:
        pass

# mail the log, if set
if mailto:
    pass

# uncomment to print when done
#print done


