import dbus

from wmii import Widget

class Battery(Widget):
    def __init__(self, name, battery='BAT0'):
        super(Battery, self).__init__(name, 'rbar')

        self._battery = self._find_battery(battery)
        if self._battery is None:
            raise KeyError('Battery "{0}" not found'.format(battery))

        self._viewtoggle = True

    def update(self):
        status = '?'
        if self.charging:
            status = '^'
        elif self.discharging:
            status = 'v'

        if self._viewtoggle:
            self.label = 'Bat: {0}{1}%'.format(status, self.percentage)
        else:
            self.label = 'Bat: {0}{1}'.format(status, self.time)

    def click(self, button):
        self._viewtoggle = not self._viewtoggle
        self.update()

    @property
    def present(self):
        return self._battery.GetProperty('battery.present')

    @property
    def charging(self):
        return self._battery.GetProperty('battery.rechargeable.is_charging')

    @property
    def discharging(self):
        return self._battery.GetProperty('battery.rechargeable.is_discharging')

    @property
    def percentage(self):
        return self._battery.GetProperty('battery.charge_level.percentage')

    @property
    def time(self):
        try:
            seconds = self._battery.GetProperty('battery.remaining_time')
        except dbus.exceptions.DBusException:
            return 'unknown'

        minutes = seconds / 60
        hours = minutes / 60

        return '{0}:{1:#02}:{2:#02}'.format(
                hours, minutes - hours * 60, seconds - minutes * 60)

    @staticmethod
    def _find_battery(name):
        bus = dbus.SystemBus()
        hal = dbus.Interface(bus.get_object('org.freedesktop.Hal',
            '/org/freedesktop/Hal/Manager'), 'org.freedesktop.Hal.Manager')

        for uid in hal.FindDeviceByCapability('battery'):
            if uid.find(name) >= 0:
                return dbus.Interface(
                        bus.get_object('org.freedesktop.Hal', uid),
                        'org.freedesktop.Hal.Device')
