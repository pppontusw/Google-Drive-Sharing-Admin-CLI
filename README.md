# Google Drive Admin CLI

Search and replace Google Drive permissions across your entire Google Apps domain.

## Prerequisites

```
httplib2==0.9.2
oauth2client==2.1.0
pyasn1==0.1.9
pyasn1-modules==0.0.8
rsa==3.4.2
six==1.10.0
```

## Setup

1. Create config.py with 

```admin = 'yoursuperadmin@googleappsdomain.com'```

2. Get a secret_key.json for a Google API project with domain wide delegation turned on and access to the following scopes:

['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/drive']

3. Use the tool as shown below:

```
usage: main.py [-h] [--simulate] [--remove-user REMOVE_USER]
               [--add-user ADD_USER] [-r {writer,reader,owner}] [-q QUERY]

View and edit large amounts of Drive permissions

optional arguments:
  -h, --help            show this help message and exit
  --simulate            Don't make changes to Google Apps
  --remove-user REMOVE_USER
                        User to remove from all files matching the criteria
  --add-user ADD_USER   User to add to all files matching the criteria
  -r {writer,reader,owner}, --role {writer,reader,owner}
                        Role to add user too (only used with --add-user)
  -q QUERY, --query QUERY
                        Query (string) to search for (ex. "'user@example.com'
                        in writers" - will find all files that
                        user@example.com can write to. "'user@example.com' in
                        writers or 'user@example.com' in readers" - will find
                        all files that user@example.com can read or write to.)
```

QUERY is any query that the Google Apps API will respond to, see documentation (here)[https://developers.google.com/drive/v3/web/search-parameters]
