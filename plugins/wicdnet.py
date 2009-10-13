import sys
import subprocess
from wicd import dbusmanager

from wmii import Widget

class Wicd(Widget):
    def __init__(self, name):
        super(Wicd, self).__init__(name, 'rbar')
        self.setup_dbus()
        self.label = 'Net:'
        print 'bar'

    def update(self):
        if self.wired.CheckIfWiredConnecting()\
                or self.wireless.CheckIfWirelessConnecting():
            self.label = 'Net: Connecting...'
            return

        if self.wired.GetWiredIP('') and self.wired.CheckPluggedIn():
            self.label = 'Net: Wired'
            return

        if self.daemon.NeedsExternalCalls():
            iwconfig = self.wireless.GetIwconfig()
        else:
            iwconfig = ''

        if self.wireless.GetWirelessIP('')\
                and self.wireless.GetCurrentNetwork(iwconfig):
            self.label = 'Net: {0}({1}%)'.format(
                    self.wireless.GetCurrentNetwork(iwconfig),
                    self.wireless.GetCurrentSignalStrength(iwconfig))
            return

        self.label = 'Net: Disconnected'

    def click(self, button):
        subprocess.Popen(('wicd-client', '-n'))

    # Borrowed from Wicd's wicd-curses.py
    def setup_dbus(self):
        dbusmanager.connect_to_dbus()
        self.bus = dbusmanager.get_bus()

        dbus_ifaces = dbusmanager.get_dbus_ifaces()
        self.daemon = dbus_ifaces['daemon']
        self.wireless = dbus_ifaces['wireless']
        self.wired = dbus_ifaces['wired']

    @staticmethod
    def check_for_wired(wired_ip, set_status):
        if wired_ip and wired.CheckPluggedIn():
            set_status(language['connected_to_wired'].replace('$A',wired_ip))
            return True
        else:
            return False
