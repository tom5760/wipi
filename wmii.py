'''
wipi - Python configuration library for Wmii
By: Tom Wambold <tom5760@gmail.com>
Heavily influenced by wmpy.
'''

import sys
import os
import logging
import time
import heapq
import subprocess
import threading

from pyxp.asyncclient import Client, OREAD, OWRITE, ORDWR
from pyxp.client import RPCError

client = Client(namespace='wmii')

class Wmii(object):
    '''Main wmii configuration object.

    Instantiate this and call .start to start the configuration.

    '''

    def __init__(self):
        self._clear_bar()
        self._colrules = Rules('/colrules')
        self._tagrules = Rules('/tagrules')

        self.ctl = Ctl('/ctl')
        self.tag = Tags()
        self.client = Clients()

        self._quit = False

        self._widgets = {}

        # Feel free to add functions to this dictionary to handle events in
        # your own way.
        self.events = {
                'CreateTag': [lambda t: self.tag.__setitem__(t, Tag(t))],
                'DestroyTag': [lambda t: self.tag.__delitem__(t)],
                'FocusTag': [lambda t: self.tag[t].focus()],
                'UnfocusTag': [lambda t: self.tag[t].unfocus()],
                'UrgentTag': [lambda type, t: self.tag[t].urgent()],
                'NotUrgentTag': [lambda type, t: self.tag[t].noturgent()],
                'Key': [lambda k: self.keybindings[k](k)],
                'LeftBarClick': [lambda b, t: self.ctl.__setattr__('view', t)],
                'RightBarClick': [lambda b, w: self._widgets[w].click(int(b))],
                'UnresponsiveClient': [self._unresponsive_client],
        }

        # Same here, your config can add actions to this dict
        self.actions = {
                'quit': self.quit,
                'restart': self.restart,
                'rehash': self.build_program_list,
        }

        self.colrules = property(self._colrules.get_rules,
                self._colrules.set_rules)
        self.tagrules = property(self._tagrules.get_rules,
                self._tagrules.set_rules)

    def action(self, action):
        '''Launch an action from the actions dictionary.'''
        try:
            self.actions[action]()
        except KeyError:
            logging.error('Invalid action "{0}"'.format(action))

    def execute(self, cmd, shell=True):
        '''Launch an external command.'''
        if not cmd:
            return

        setsid = getattr(os, 'setsid', None)
        if not setsid:
            setsid = getattr(os, 'setpgrp', None)

        return subprocess.Popen(cmd, shell=shell, preexec_fn=setsid)

    def register_widget(self, widget):
        '''Adds a widget to be polled by the event loop.'''
        self._widgets[widget.name] = widget

    def menu(self, items):
        '''Shows a menu using wimenu and returns the users choice.'''
        wimenu = subprocess.Popen(['wimenu'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
        for item in items:
            wimenu.stdin.write('{0}\n'.format(item))
        wimenu.stdin.close()
        return wimenu.stdout.read().strip()

    def tag_menu(self):
        '''Shortcut to show a menu of tags.'''
        return self.menu(sorted(map(lambda x: x.name, self.tag)))

    def action_menu(self):
        '''Shortcut to show a menu of actions.'''
        return self.menu(sorted(self.actions.keys()))

    def program_menu(self):
        '''Shortcut to show a menu of programs.'''
        return self.menu(self.program_list)

    def build_program_list(self):
        '''Caches a list of programs for the program menu.'''
        self.program_list = []
        for path in os.environ['PATH'].split(':'):
            try:
                pathlist = os.listdir(path)
            except OSError:
                continue
            for bin in os.listdir(path):
                binpath = '/'.join((path, bin))
                if os.path.isfile(binpath) and os.access(binpath, os.X_OK):
                    self.program_list.append(bin)

    def restart(self):
        '''Restart configuration'''
        self.execute(os.path.abspath(sys.argv[0]))
        self._quit = True
        sys.exit()

    def quit(self):
        '''Quits wmii.'''
        self.ctl.write('quit')
        self._quit = True
        sys.exit(100)

    def start(self, timeout=1):
        '''Starts the event loop.  Monitors widgets with interval "timeout".'''
        # Tell wmii what keys to listen for
        client.write('/keys', '\n'.join(self.keybindings.keys()))

        # Focus the currently selected tag
        self.tag['sel'].focus()

        # Start reading events
        client.areadlines('/event', self._handle_event)

        # Monitor widgets
        while True:
            if self._quit:
                sys.exit()
            for widget in self._widgets.values():
                try:
                    widget.update()
                except Exception as e:
                    logging.error('Exception in widget {0}: {1}'
                            .format(widget.name, e))
            time.sleep(timeout)

    def _handle_event(self, event):
        '''Calls event handlers when events happen.'''
        event = event.split()
        try:
            handlers = self.events[event[0]]
        except KeyError:
            return
        for handler in handlers:
            try:
                handler(*event[1:])
            except Exception as e:
                logging.error('Exception on event {0}: {1}'
                        .format(' '.join(event[1:]), e))

    def _clear_bar(self):
        '''Clears the bar of all widgets.'''
        for file in client.readdir('/rbar'):
            client.remove('/rbar/{0}'.format(file.name))
        for file in client.readdir('/lbar'):
            client.remove('/lbar/{0}'.format(file.name))

    def _unresponsive_client(self, client):
        '''Called if a client becomes unresponsive.'''
        wihack = subprocess.Popen(['wihack', '-transient', client,
            'xmessage', '-nearmouse', '-buttons', 'Kill,Wait', '-print',
            'Client %s is not responding.  '
            'What do you want to do?' % get_ctl('/client/%s/label' % client)
            ])
        # The [:-1] removes the "\n" from the output
        resp = wihack.communicate()[0][:-1]
        if resp == 'Kill':
            self.client[client].ctl = 'slay'

class Ctl(object):
    '''Frontend to ctl files'''
    def __init__(self, path):
        self.__dict__['file'] = client.open(path, ORDWR)

    def write(self, value):
        self.file.write(value)

    def __getattr__(self, key):
        rv = None
        for line in self.file.readlines():
            if line.startswith(key):
                # Only return the part after the key
                rv = line[line.index(' ') + 1:]
        self.file.offset = 0
        return rv

    def __setattr__(self, key, value):
        self.write(' '.join((key, value)))

class Rules(object):
    '''Frontend for the /colrules and /tagrules files.'''
    def __init__(self, path):
        self.file = client.open(path, ORDWR)

    def get_rules(self):
        rules = {}
        for line in self.file.readlines():
            key, value = line.split(' -> ')
            # The 1:-1 is to remove the slashes
            rules[key[1:-1]] = value
        self.file.offset = 0
        return rules

    def set_rules(self, dict):
        self.file.write(self.path,
                '\n'.join(['/{key}/ -> {value}'.format(key=k, value=v)
                    for k, v in dict.items()]))

class Tag(object):
    '''Frontend for a tag object (including widget).'''
    def __init__(self, name):
        self.name = name
        self.ctl = Ctl('/tag/{0}/ctl'.format(name))
        self.mainctl = Ctl('/ctl')
        self.widget = Widget(name, 'lbar', self.mainctl.normcolors, name)

    def focus(self):
        self.widget.color = self.mainctl.focuscolors

    def unfocus(self):
        self.widget.color = self.mainctl.normcolors

    def urgent(self):
        self.widget.label = '*{0}'.format(self.widget.label)

    def noturgent(self):
        self.widget.label = self.widget.label[1:]

class Tags(object):
    '''Container for all tags in the system.'''
    path = '/tag'
    item = Tag

    def __init__(self):
        self.items = {}
        for file in filter(lambda x: x.name != 'sel', client.readdir(self.path)):
            self.items[file.name] = self.item(file.name)

    def __iter__(self):
        return self.items.itervalues()

    def __getitem__(self, key):
        try:
            return self.items[key]
        except KeyError:
            if key == 'sel':
                sel = client.readlines('{0}/sel/ctl'.format(self.path)).next()
                return self[sel]
            self.items[key] = self.item(key)
            return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    def __delitem__(self, key):
        try:
            del self.items[key]
        except KeyError:
            client.remove('/lbar/{0}'.format(key))

class Client(object):
    '''Frontend for a client.'''
    def __init__(self, name):
        self.ctl = Ctl('/client/{0}/ctl'.format(name))
        self._tags = client.open('/client/{0}/tags'.format(name), ORDWR)

    def get_tags(self):
        return self._tags.read(offset=0)

    def set_tags(self, value):
        self._tags.write(value)

    tags = property(get_tags, set_tags)

class Clients(Tags):
    '''Container for all clients.'''
    path = '/client'
    item = Client

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

class Widget(object):
    '''Widget on the bar.'''
    def __init__(self, name, bar, color=None, label=None):
        self.name = name
        self.bar = bar
        self.file = client.create('/{0.bar}/{0.name}'.format(self), ORDWR)

        if color is not None:
            self.color = color

        if label is not None:
            self.label = label

    def get_color(self):
        return ' '.join(self.file.read(offset=0).split()[:-1])

    def set_color(self, value):
        self.file.write(' '.join((value, self.label)))

    def get_label(self):
        return self.file.read(offset=0).split()[-1]

    def set_label(self, value):
        self.file.write(value)

    def click(self, button):
        pass

    color = property(get_color, set_color)
    label = property(get_label, set_label)

    def __del__(self):
        self.file.remove()
