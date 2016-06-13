import json
import httplib2
from oauth2client import client
from oauth2client.service_account import ServiceAccountCredentials
import urllib
import re
import logging
from config import admin
import sys
import datetime

logging.getLogger("oauth2client").setLevel(logging.WARNING)
logger = logging.getLogger('driveadmin')
logger.setLevel(logging.INFO)
file = logging.FileHandler('driveadmin.log')
file.setLevel(logging.INFO)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file.setFormatter(logging.Formatter('%(message)s'))
console.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(file)
logger.addHandler(console)


SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/drive']
APPLICATION_NAME = 'Google Drive Sharing Admin'

try:
    import argparse
    flags = argparse.ArgumentParser(description='View and edit large amounts of Drive permissions')
    flags.add_argument('--simulate', action='store_true', help='Don\'t make changes to Google Apps')
    flags.add_argument('--remove-user', action='append', help='User to remove from all files matching the criteria')
    flags.add_argument('--add-user', action='append', help='User to add to all files matching the criteria')
    flags.add_argument('-r', '--role', action='store', help='Role to add user too (only used with --add-user)', choices=['writer', 'reader', 'owner'])
    flags.add_argument('-q', '--query', action='store', help='Query (string) to search for (ex. \"\'user@example.com\' in writers\" - will find all files that user@example.com can write to.\n\"\'user@example.com\' in writers or \'user@example.com\' in readers\" - will find all files that user@example.com can read or write to.)')
    flags = flags.parse_args()
    if flags.add_user and flags.role is None:
    	print("--add-user requires --role be specified.")
    	exit()
except ImportError:
    print 'Can\'t parse arguments, abort!'
    exit()

def main():
	logger.info('RUN STARTED AT %s with query "%s". Simulation is %s. Adding users %s with role %s. Removing users %s.' % (datetime.datetime.now(), flags.query, flags.simulate, flags.add_user, flags.role, flags.remove_user))
	all_users = listUsers()
	itemsmatch = []
	for index,user in enumerate(all_users):
		itemsobj = {'user': user, 'items': []}
		logger.info('Checking user %s (%d of %d)' % (user,index+1,len(all_users)))
		useritems = getItems(user)
		if useritems:
			logger.info('Found %d items!' % len(useritems))
			for index,item in enumerate(useritems):
				logger.debug('Found item %s (%d of %d)' % (item['title'],index+1,len(useritems)))
				itemsobj['items'].append(item)
			if flags.add_user:
				results = insertItems(itemsobj['user'], itemsobj, flags.add_user, flags.role, 'user')
				if results['successarray'] or results['failarray']:
					if 'successarray' not in results:
						successarray = False
					else:
						successarray = results['successarray']
					if 'failarray' not in results:
						failarray = False
					else:
						failarray = results['failarray']
					printInsertResults(successarray, failarray)
			if flags.remove_user:
				results = deleteItems(itemsobj['user'], itemsobj, flags.remove_user)
				if results['successarray'] or results['failarray']:
					if 'successarray' not in results:
						successarray = False
					else:
						successarray = results['successarray']
					if 'failarray' not in results:
						failarray = False
					else:
						failarray = results['failarray']
					printDeleteResults(successarray, failarray)
	exit()

def getItems(user):
	if flags.query:
		drivesearchquery = flags.query
	else:
		drivesearchquery = False
	credentials = authenticate(user)
	http_auth = credentials.authorize(httplib2.Http())
	url_get = 'https://www.googleapis.com/drive/v2/files?'
	url_get += makeQuery(drivesearchquery, user, False)
	content = http_auth.request(url_get, "GET")
	if content[0]['status'] == '400':
		logger.info(content[1])
		exit()
	info = json.loads(content[1])
	itemarray = []
	while 'nextPageToken' in info:
		itemarray += buildItems(info)
		url_get = 'https://www.googleapis.com/drive/v2/files?'
		url_get += makeQuery(drivesearchquery, user, info['nextPageToken'])
		content = http_auth.request(url_get, "GET")
		info = json.loads(content[1])
	itemarray += buildItems(info)
	return itemarray


def deleteItems(user, items, usertodelete):
	credentials = authenticate(user)
	http_auth = credentials.authorize(httplib2.Http())	
	successarray = []
	failarray = []
	for us in usertodelete:
		url_get = 'https://www.googleapis.com/drive/v2/permissionIds/' + us
		content = http_auth.request(url_get)
		if content[0]['status'] == '200' or content[0]['status'] == '200':
			info = json.loads(content[1])
			permissionID = info['id']				
			for item in items['items']:
				if flags.simulate:
					logger.info('%s would have been deleted from the file %s' % (us, item['title']))
				else:
					url_get = 'https://www.googleapis.com/drive/v2/files/' + item['id'] + '/permissions/' + permissionID
					content = http_auth.request(url_get, "DELETE")
					if content[0]['status'] == '200' or content[0]['status'] == '204':
						successobj = {'id': item['id'],'title': item['title'], 'moduser': us, 'message': 'Successfully removed' }
						successarray.append(successobj)
					else:
						failobj = {'id': item['id'],'title': item['title'], 'moduser': us, 'message': json.loads(content[1])['error']['message'] }
						failarray.append(failobj)
		else:
			logger.warning('User not found')
	return {'successarray': successarray, 'failarray': failarray}


def insertItems(user, items, usertoadd, role, typeofuser):
	successarray = []
	failarray = []
	for us in usertoadd:
		payload = "{\"role\": \"%s\", \"type\": \"%s\", \"value\": \"%s\"}" % (role, typeofuser, us)
		a = payload.encode('utf-8')
		credentials = authenticate(user)
		http_auth = credentials.authorize(httplib2.Http())
		for item in items['items']:
			if flags.simulate:
					logger.info('%s would have been added to the file %s' % (us, item['title']))
			else:
				url_get = 'https://www.googleapis.com/drive/v2/files/' + item['id'] + '/permissions?sendNotificationEmails=false'
				content = http_auth.request(url_get, method="POST", body=a, headers={'Content-Type': 'application/json'})
				if content[0]['status'] == '200' or content[0]['status'] == '204':
					successobj = {'id': item['id'],'title': item['title'], 'moduser': us, 'message': 'Successfully added' }
					successarray.append(successobj)
				else:
					failobj = {'id': item['id'],'title': item['title'], 'moduser': us, 'message': json.loads(content[1])['error']['message'] }
					failarray.append(failobj)

	return {'successarray': successarray, 'failarray': failarray}


def listUsers():
	credentials = authenticate(admin)
	http_auth = credentials.authorize(httplib2.Http())
	url_get = 'https://www.googleapis.com/admin/directory/v1/users?customer=my_customer'
	content = http_auth.request(url_get, "GET")
	users = json.loads(content[1])
	userarray = []
	while 'nextPageToken' in users:
		token = users['nextPageToken']
		userlist = users['users']
		for user in userlist:
			userarray.append(user['primaryEmail'])
		url_get = 'https://www.googleapis.com/admin/directory/v1/users?customer=my_customer&pageToken=' + token
		content = http_auth.request(url_get, "GET")
		users = json.loads(content[1])
	userlist = users['users']
	for user in userlist:
		userarray.append(user['primaryEmail'])
	return userarray

def printInsertResults(successarray, failarray):
	if successarray:
		logger.info('======SUCCEEDED======')
		for item in successarray:
			logger.info('Added %s to %s' % (item['moduser'], item['title']))
	if failarray:
		logger.info('======FAILED======')
		for item in failarray:
			logger.warning('Failed to add %s to %s' % (item['moduser'], item['title']))
			logger.info('Error: %s' % item['message'])
	return None


def printDeleteResults(successarray, failarray):
	if successarray:
		logger.info('======SUCCEEDED======')
		for item in successarray:
			logger.info('Removed %s from %s' % (item['moduser'], item['title']))
	if failarray:
		logger.info('======FAILED======')
		for item in failarray:
			logger.warning('Failed to remove %s from %s' % (item['moduser'], item['title']))
			logger.info('Error: %s' % item['message'])
	return None

def authenticate(user):
	# get credentials
    credentials = ServiceAccountCredentials.from_json_keyfile_name('secret_key.json', SCOPES)
    # delegate to superadmin
    delegated_credentials = credentials.create_delegated(user)
    # put credentials in session
    return delegated_credentials


def buildItems(info):
	itemarray = []
	try:
		infolist = info['items']
		for item in infolist:
			itemobj = { 'title': item['title'], 'id': item['id'] }
			itemarray.append(itemobj)
		return itemarray
	except KeyError:
		try:
			logging.warning('Something wen\'t wrong when fetching items: %s ' % infolist)
		except UnboundLocalError:
			logging.warning('Something wen\'t wrong when fetching items, info seems to be empty.')
		return None


def makeQuery(drivesearchquery, user, token):
	if drivesearchquery != False and token:
		query = urllib.urlencode({'q': '(' + drivesearchquery + ') and \'' + user + '\' in owners', 'pageToken': token})
	elif drivesearchquery != False and token == False:
		query = urllib.urlencode({'q': '(' + drivesearchquery + ') and \'' + user + '\' in owners'})
	elif drivesearchquery == False and token:
		query = urllib.urlencode({'q': '\'' + user + '\' in owners', 'pageToken': token})
	elif drivesearchquery == False and token == False:
		query = urllib.urlencode({'q': '\'' + user + '\' in owners'})
	else:
		logger.error('No query could be constructed')
		exit()
	return query

if __name__ == '__main__':
	main()