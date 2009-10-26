from wmii import Widget

class Spacer(Widget):
    def __init__(self, name):
        super(Spacer, self).__init__(name, 'rbar')

    def update(self):
        pass
