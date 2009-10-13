from alsaaudio import Mixer, ALSAAudioError

from wmii import Widget

class Volume(Widget):
    def __init__(self, name, voldev='Master', mutedev='Master', step=2):
        super(Volume, self).__init__(name, 'rbar')
        self.voldev = voldev
        self.mutedev = mutedev
        self.step = step
        self.update()

    def update(self):
        if bool(Mixer(self.mutedev).getmute()[0]):
            self.label = 'Vol: Mute'
        else:
            self.label = 'Vol: {0}%'.format(Mixer(self.voldev).getvolume()[0])

    def click(self, button):
        if button == 1:
            mixer = Mixer(self.mutedev)
            mixer.setmute(not bool(mixer.getmute()[0]))

        elif button == 4:
            mixer = Mixer(self.voldev)
            try:
                mixer.setvolume(mixer.getvolume()[0] + self.step)
            except ALSAAudioError:
                return

        elif button == 5:
            mixer = Mixer(self.voldev)
            try:
                mixer.setvolume(mixer.getvolume()[0] - self.step)
            except ALSAAudioError:
                return

        self.update()
