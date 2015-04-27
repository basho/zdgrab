"""
zdgrab: Download attachments from Zendesk tickets
"""
from __future__ import unicode_literals
import os, textwrap
import configparser

from zdgrab.zdsplode import zdsplode

def zdgrab(zd, agent='me', ticket_ids=None,
           work_dir=os.path.join(os.path.expanduser('~'), 'zdgrab'),
           verbose=False):

    import urllib, base64

    # dict of paths to attachments retrieved to return. format is:
    # { 'path/to/ticket/1': [ 'path/to/attachment1', 'path/to/attachment2' ],
    #   'path/to/ticket/2': [ 'path/to/attachment1', 'path/to/attachment2' ] }
    grabs = {}

    # Save the current directory so we can go back once done
    start_dir = os.getcwd()

    # Normalize all of the given paths to absolute paths
    work_dir = os.path.abspath(work_dir)

    # Check for and create working directory
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)

    # Change to working directory to begin file output
    os.chdir(work_dir)

    if ticket_ids:
        # ticket_ids given, query for those
        query=','.join([s for s in map(str,ticket_ids)])
        if verbose:
                        print "Query: {}".format(query) 
        #response = zd.search(query=query)
        res = zd.show_many_tickets(ids=query)
        if verbose:
                        print('{}'.format(res))
        response = {}
        response['count'] = 0
        response['results'] = []
        for resp in res['tickets']:
            response['count'] += 1
            resp['result_type'] = 'ticket'
            response['results'].append(resp)
            if verbose:
                print('found: {}'.format(resp['id']))

    else:
        # List of tickets not given. Get all of the attachments for all of this
        # user's open tickets.
        response = zd.search(query='status<solved assignee:{}'.format(agent))

    if response['count'] == 0:
        # No tickets from which to get attachments
        print("No tickets provided for attachment retrieval.")
        return {}

    # Fix up some headers to use for downloading the attachments.
    # We're going to borrow the zendesk object's httplib client.
    headers = {}
    if zd.zendesk_username is not None and zd.zendesk_password is not None:
        headers["Authorization"] = "Basic %s" % (
            base64.b64encode(zd.zendesk_username + ':' +
                             zd.zendesk_password))

    # Get the attachments from the given zendesk tickets
    for ticket in response['results']:
        if ticket['result_type'] != 'ticket':
            # This is not actually a ticket. Weird. Skip it.
            continue

        if verbose: 
            print('Ticket {}'.format(ticket['id']))

        ticket_dir = os.path.join(work_dir, str(ticket['id']))
        ticket_com_dir = os.path.join(ticket_dir, 'comments')
        comment_num = 0
        audits = zd.list_audits(ticket_id=ticket['id'])['audits']
        for audit in audits:
            for event in audit['events']:
                if event['type'] != 'Comment':
                    # This event isn't a comment. Skip it.
                    continue

                comment_num += 1
                comment_dir = os.path.join(ticket_com_dir, str(comment_num))

                if verbose and event['attachments']:
                    print('Comment {}'.format(comment_num))

                for attachment in event['attachments']:
                    name = attachment['file_name']
                    if os.path.isfile(os.path.join(comment_dir, name)):
                        if verbose:
                            print('Attachment {} already present'.format(name))
                        continue

                    # Get this attachment
                    if verbose: 
                        print('Attachment {}'.format(name))

                    # Check for and create the download directory
                    if not os.path.isdir(comment_dir):
                        os.makedirs(comment_dir)

                    os.chdir(comment_dir)
                    response, content = zd.client.request(attachment['content_url'], headers=headers)
                    if response['status'] != '200':
                        print('Error downloading {}'.format(attachment['content_url']))
                        continue

                    with open(name, 'wb') as f:
                        f.write(content)

                    # Check for and create the grabs entry to return
                    if not grabs.has_key(ticket_dir):
                        grabs[ticket_dir] = []

                    grabs[ticket_dir].append(
                        os.path.join('comments', str(comment_num), name) )

                    # Let's try to extract this if it's compressed
                    zdsplode(name, verbose=verbose)

    os.chdir(start_dir)
    return grabs

def config_state(config_file, section, state):
    """
    Update a state (a dictionary) with options from a file parsed by
    configparser for a config [section]. May throw configparser.NoSectionError.

    Handles Boolean values specially by looking at the current state for
    booleans and updating those values specially with configparser.getboolean
    """

    # A list of program state items which are booleans.
    # Kept for convience as they are treated specially when parsing configs.
    state_bools = [k for k, v in state.iteritems() if isinstance(v, bool)]

    # read the config file
    config = configparser.SafeConfigParser()
    config.read(config_file)

    # look for the section, make it a dictionary
    config_dict = dict(config.items(section))

    # Treat bool values specially using getboolean (allows for 1, yes, true)
    for k in state_bools:
        try:
            config_dict[k] = config.getboolean(section, k)
        except configparser.NoOptionError:
            # This config file did not contain this option. Skip it.
            pass

    # Convert any new strings to full unicode
    for k in [k for k, v in config_dict.iteritems() if isinstance(v, str)]:
        config_dict[k] = config_dict[k].decode('utf-8')

    # update the state with the section dict
    state.update(config_dict)

def config(argv=None):
    import os, sys, argparse

    # Declare a class for an argparse custom action.
    # Handles converting ascii input from argparse that may contain unicode
    # to a real unicode string.
    class UnicodeStore(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values.decode('utf-8'))

    # Options precedence:
    # program state defaults, which are overridden by
    # ~/.zd.cfg [zdgrab] section options, which are overridden by
    # command line options, which are overridden by
    # -c CONFIG_FILE [zdgrab] section options, which are overridden by
    # ~/.zd.cfg [RUN_SECTION] section options, which are overridden by
    # -c CONFIG_FILE [RUN_SECTION] section options
    #
    # Program state, with defaults
    #
    state = {
        'verbose': False,
        'tickets': None,
        'work_dir': os.path.join(os.path.expanduser('~'), 'zdgrab'),
        'agent': 'me',
        'url': None,
        'mail': None,
        'password': 'prompt',
        'is_token': False,
    }

    argp = argparse.ArgumentParser(
        description='Download attachments from Zendesk tickets.')
    argp.add_argument('-v', '--verbose', action='store_true',
        help='Verbose output')

    argp.add_argument('-t', action=UnicodeStore, dest='tickets',
        help='Ticket(s) to grab attachments (default: all of your open tickets)')

    argp.add_argument('-c', action=UnicodeStore, dest='config_file',
        help='Configuration file (overrides ~/.zd.cfg)')

    argp.add_argument('-w', action=UnicodeStore, dest='work_dir',
        help="""Working directory in which to store attachments.
        (default: ~/zdgrab/)""")

    argp.add_argument('-a', action=UnicodeStore, dest='agent',
        help='Agent whose open tickets to search (default: me)')

    argp.add_argument('-u', action=UnicodeStore, dest='url',
        help='URL of Zendesk (e.g. https://example.zendesk.com)')
    argp.add_argument('-m', action=UnicodeStore, dest='mail',
        help='E-Mail address for Zendesk login')
    argp.add_argument('-p', action=UnicodeStore, dest='password',
        help='Password for Zendesk login',
        nargs='?', const=state['password'])
    argp.add_argument('-i', '--is-token', action='store_true', dest='is_token',
        help='Is token? Specify if password supplied a Zendesk token')

    # Set argparse defaults with program defaults.
    # Skip password as it is argparse const, not argparse default
    argp.set_defaults(**dict((k, v) for k, v in state.iteritems() if k != 'password'))

    # Read ~/.zd.cfg [zdgrab] section and update argparse defaults
    try:
        config_state(os.path.join(os.path.expanduser('~'), '.zd.cfg'), 'zd', state)
        # Password is OK now, because we either have one from the config file or
        # it is still None.
        argp.set_defaults(**dict((k, v) for k, v in state.iteritems()))
    except configparser.NoSectionError:
        # -c CONFIG_FILE did not have a [zdgrab] section. Skip it.
        pass

    # Parse the command line options
    if argv is None:
        argv = sys.argv
    args = argp.parse_args()

    # Update the program state with command line options
    for k in state.keys():
        state[k] = getattr(args, k)

    # -c CONFIG_FILE given on command line read args.config_file [zdgrab], update state
    if args.config_file:
        if state['verbose']: print('Reading config file {}'.format(args.config_file))
        try:
            config_state(args.config_file, 'zd', state)
        except configparser.NoSectionError:
            # -c CONFIG_FILE did not have a [zdgrab] section. Skip it.
            pass

    from zendesk import Zendesk
    if state['url'] and state['mail'] and state['password']:
        if state['verbose']:
            print('Configuring Zendesk with:\n'
                  '  url: {}\n'
                  '  mail: {}\n'
                  '  is_token: {}\n'
                  '  password: (hidden)\n'.format( state['url'], state['mail'],
                                         repr(state['is_token']) ))
        zd = Zendesk(state['url'],
                    zendesk_username = state['mail'],
                    zendesk_password = state['password'],
                    use_api_token = state['is_token'],
                    api_version=2)
    else:
        msg = textwrap.dedent("""\
            Error: Need Zendesk config to continue. Use -u, -m, -p options
            or a config file to provide the information.

            Config file (e.g. ~/.zd.cfg) should be something like:
            [zd]
            url = https://example.zendesk.com
            mail = you@example.com
            password = dneib393fwEF3ifbsEXAMPLEdhb93dw343
            is_token = 1
            agent = agent@example.com
            """)
        print(msg)
        return 1

    # Log the state
    if state['verbose']:
        print('Running with program state:')
        # Let's go around our ass to get to our elbow to hide the password here.
        for (k, v) in [(k, v) for k, v in state.iteritems() if k != 'password']:
            print('  {}: {}'.format(k, repr(v)))
        print('  password: (hidden)\n')

    # tickets=None means default to getting all of the attachments for this
    # user's open tickets. If tickets is given, try to split it into ints
    if state['tickets']:
        # User gave a list of tickets
        try:
            state['tickets'] = [int(i) for i in state['tickets'].split(',')]
        except ValueError:
            print('Error: Could not convert to integers: {}'.format(state['tickets']))
            return 1

    return zd, state

def main(argv=None):
    zd, state = config(argv)
    zdgrab(zd, state['agent'], state['tickets'], state['work_dir'], state['verbose'])
    return 0

