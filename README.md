# Download attachments from Zendesk tickets

Zdgrab is a utility for downloading attachments to tickets from
[Zendesk](http://www.zendesk.com) and extracting and arranging them.

## Installing

Tested with Python 2.7. Zdgrab requires configparser and the [patched
zendesk](http://github.com/eventbrite/zendesk) Python module, which has its own
requirements. Simplejson may not be strictly required by zendesk, but is
suggested.

```
pip install https://github.com/eventbrite/zendesk/archive/master.zip
pip install https://github.com/basho/zdgrab/archive/master.zip
```

You may wish to use easy_install instead of pip, and use a virtualenv.

## Zendesk API Token Setup

Note: Users can use a Zendesk shared account and its access token. In this
shared account setup, set 'mail' to the shared account, and set 'agent' to your
email address in the configuration file.

Prior to using zdgrab, a Zendesk API token must be generated for the account
that will be used. This token helps avoid disclosing the Zendesk user account
password, and it can be regenerated or disabled altogether at any time.

To create a Zendesk API token for use with zdgrab, follow these steps:

1. Log into your Zendesk website: https://example.zendesk.com
2. Navigate to the API settings: https://example.zendesk.com/settings/api/
3. Click the **Enabled** checkbox inside the **Token Access** section.
4. Make note of the 40 character string after *Your API token is:*
5. Click Save.

**NOTE**: If problems occur with step #3 above, the account used to access
Zendesk could lack the necessary permissions to work with an API token. In this
case, appropriate permissions should be requested from your administrator.

Once the Zendesk API token is configured, and noted, proceed to configuring
a Python virtual environment.

### Configuration

Options when running zdgrab can be configured through configuration files.  An
example of using two config files is given below.

    # ~/.zd.cfg
    [zd]
    mail = you@example.com
    password = dneib393fwEF3ifbsEXAMPLEdhb93dw343
    url = https://example.zendesk.com
    is_token = 1
    agent = agent@example.com

### Usage

The script can be invoked with the following synopsis:

    usage: zdgrab [-h] [-v] [-t TICKETS] [-c CONFIG_FILE] [-w WORK_DIR] [-a AGENT]
                  [-u URL] [-m MAIL] [-p [PASSWORD]] [-i]

    Download attachments from Zendesk tickets.

    optional arguments:
      -h, --help      show this help message and exit
      -v, --verbose   Verbose output
      -t TICKETS      Ticket(s) to grab attachments (default: all of your open
                      tickets)
      -c CONFIG_FILE  Configuration file (overrides ~/.zd.cfg)
      -w WORK_DIR     Working directory in which to store attachments. (default:
                      ~/zdgrab/)
      -a AGENT        Agent whose open tickets to search (default: me)
      -u URL          URL of Zendesk (e.g. https://example.zendesk.com)
      -m MAIL         E-Mail address for Zendesk login
      -p [PASSWORD]   Password for Zendesk login
      -i, --is-token  Is token? Specify if password supplied a Zendesk token

Here are some basic zdgrab usage examples to get started:

#### Help

    zdgrab -h

#### Get/update all attachment for your open tickets

    zdgrab

#### Get/update all attachments for your open tickets with verbose output

    zdgrab -v

#### Get/update all attachments from a specific ticket

    zdgrab -t 2940

#### Get/update all attachments from a number of specific tickets

    zdgrab -t 2940,3405,3418

## Notes

* zdgrab uses Zendesk API version 2 with JSON
* zdgrab depends on the following Python modules:
 * configparser
 * zendesk (patched for APIv2), which depends on:
   * httplib2
   * simplejson (recommended)

### TODO

I would like to make the code into a class to further promote reuse. Also, I'd
like to factor the configuration out to its own module and generalize it.

### Resources

* Python Zendesk module: https://github.com/eventbrite/zendesk
* Zendesk Developer Site (For API information): http://developer.zendesk.com

### Using zdgrab as a module

It can be useful to script zdgrab using Python. The configuration is performed
followed by the zdgrab, then the return value of the zdgrab can then be used to
operate on the attachments and directories that were grabbed. For example:

```
#!/usr/bin/env python

import os
from zdgrab import config, zdgrab

if __name__ == '__main__':
    zd, state = config()
    grabs = zdgrab(zd, state['agent'], state['tickets'], state['work_dir'],
                   state['verbose'])

    start_dir = os.path.abspath(os.getcwd())

    for ticket_dir, attach_path in grabs.iteritems():
        # Path to the ticket dir containing the attachment
        # os.chdir(ticket_dir)

        # Path to the attachment that was grabbed
        # os.path.join(ticket_dir, attach_path)

        # Path to the comments dir in this ticket dir
        ticket_com_dir = os.path.join(ticket_dir, 'comments')

        # Handy way to get a list of the comment dirs in numerical order:
        comment_dirs = [dir for dir in os.listdir(ticket_com_dir) if dir.isdigit()]
        comment_dirs = map(int, comment_dirs) # convert to ints
        comment_dirs.sort()                   # sort them
        comment_dirs = map(str, comment_dirs) # convert back to strings

        # Iterate through the dirs and over every file
        os.chdir(ticket_com_dir)
        for comment_dir in comment_dirs:
            for dirpath, dirnames, filenames in os.walk(comment_dir):
                for filename in filenames:
                    print(os.path.join(ticket_com_dir, dirpath, filename))

    os.chdir(start_dir)
```

