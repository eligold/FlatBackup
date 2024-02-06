### Example evtest touch input frame:
# Event: time 1707153627.150887, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 253
# Event: time 1707153627.150887, type 3 (EV_ABS), code 0 (ABS_X), value 1057
# Event: time 1707153627.150887, type 3 (EV_ABS), code 1 (ABS_Y), value 253
# Event: time 1707153627.150887, type 4 (EV_MSC), code 5 (MSC_TIMESTAMP), value 0
# Event: time 1707153627.150887, -------------- SYN_REPORT ------------
class touchEvent():
    isX = False
    isY = False
    valid = True

    def __init__(self, line):
            try:
                segments = line.strip().split(", ")
                self.time = float(segments[0].lstrip("Eventim: "))
                frame = segments[1:]
                if len(frame) > 1:
                    event = frame[0].lstrip("type ").rstrip(")").split(" (")
                    self.event_id = int(event[0])
                    self.event = event[1]
                    code = frame[1].lstrip("code ").rstrip(")").split(" (")
                    self.code_id = int(code[0])
                    if code == 0:
                        self.isX = True
                    elif code == 1:
                        self.isY = True
                    self.code = code[1]
                    self.value = int(frame[-1].lstrip("value ").rstrip())
                else:
                    self.value = frame[0]
                    self.valid = False
            except: self.value = f'error for line:\n{line}'

    def pretty(self):
        if self.valid:
            return f'{self.event}[{self.event_id}]: {self.code}[#{self.code_id}] -> {self.value}'