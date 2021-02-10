import utime
from machine import Pin

########################################################################
## Constants
########################################################################
CFG_FILENAME = "options.cfg"

class AutoRate:
    HZ_1    = ("1hz",    30, 30)
    HZ_2    = ("2hz",    15, 15)
    HZ_3    = ("3hz",    10, 10)
    HZ_3p75 = ("3.75hz", 8, 8)
    HZ_5    = ("5hz",    6, 6)
    HZ_6    = ("6hz",    5, 5)
    HZ_7p5  = ("7.5hz",  4, 4)
    HZ_10   = ("10hz",   3, 3)
    HZ_15   = ("15hz",   2, 2)
    HZ_30   = ("30hz",   1, 1)
    HZ_60   = ("60hz",   1, 0)

########################################################################
## Button definitions
########################################################################

class ProgramButton:
    """Represents button used to program autofire config."""
    def __init__(self, pin_no):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)

class JammaButton:
    """Represents a jamma "button". This is what's connected to the PCB."""
    def __init__(self, pin_no, name):
        self.pin = Pin(pin_no, Pin.OPEN_DRAIN)
        self.name = name
        self.should_fire = False
    def maybe_fire(self):
        """Fire if 'should_fire' was marked True."""
        if self.should_fire:
            self.pin.off()
            self.should_fire = False
        else:
            self.pin.on()

class CabButton:
    """Represents a physical button of a cabinet. Connects to cab panel."""
    def __init__(self, pin_no, name):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self.name = name
        self.out_button = None
        self.auto_rate = "N/A"
        self.active = 1
        self.inactive = 0
        self.ticks = 0
    def debounce(self):
        """Util to avoid duplicate inputs of same button during programming."""
        while self.pin.value() == 0: pass
        utime.sleep_ms(250)
    def program(self, out_button, auto_rate):
        """Set autofire rate of a cab button. Expects a 'AutoRate' constant."""
        print("Programming %s to %s with %s" % (self.name, out_button.name, auto_rate[0]))
        self.out_button = out_button
        self.auto_rate, self.active, self.inactive = auto_rate[0:3]
    def fire_if_pressed(self):
        """Marks the connected output button to fire, if autofire frequence allows it."""
        if self.out_button and self.pin.value() == 0:
            if self.ticks < self.active:
                self.out_button.should_fire = True
            self.ticks += 1
            if self.ticks >= (self.active + self.inactive):
                self.ticks = 0
    def serialized_state(self):  # TODO: move out?
        """Serialize the internal state for storage."""
        return "%s %s %d %d %s\n" % (self.name, self.out_button.name,
                                     self.active, self.inactive, self.auto_rate)
    def restore_state(self, line, out_jams): # TODO: move out?
        """Restore state from stored representation."""
        _, out_name, active, inactive, self.auto_rate = line.strip().split()
        for jam in out_jams:
            if jam.name == out_name:
                self.out_button = jam
        self.active = int(active)
        self.inactive = int(inactive)

def program(cabs, jams):
    def get_in_btn(cabs):
        while True:
            utime.sleep_ms(100)
            for cab in cabs:
                if cab.pin.value() == 0:
                    cab.debounce()
                    return cab
    def get_out_btn(cabs, jams):
        while True:
            utime.sleep_ms(100)
            for i, cab in enumerate(cabs):
                if cab.pin.value() == 0:
                    cab.debounce()
                    return jams[i]
    def get_auto_rate(cabs):
        while True:
            utime.sleep_ms(100)
            for i, cab in enumerate(cabs):
                if cab.pin.value() == 0:
                    cab.debounce()
                    if i == 0: return AutoRate.HZ_60
                    elif i == 1: return AutoRate.HZ_15
                    elif i == 2: return AutoRate.HZ_6
                    else: return AutoRate.HZ_2
    print("Starting programming")
    print("Get in button")
    in_btn = get_in_btn(cabs)
    print("Got " + in_btn.name)
    print("Get out button")
    out_btn = get_out_btn(cabs, jams)
    print("Got " + out_btn.name)
    print("Get auto rate")
    auto_rate = get_auto_rate(cabs)
    in_btn.program(out_btn, auto_rate)
    save_settings(cabs, jams)

def load_settings(cabs, jams):
    print("Loading settings")
    try:
        f = open(CFG_FILENAME)
        for i, line in enumerate(f.readlines()):
            print("Read: " + line.strip())
            cabs[i].restore_state(line, jams) 
        f.close()
    except Exception as e:
        print("Failed reading setting")
        print(e)
        for i, btn in enumerate(cabs):
            btn.program(jams[i], AutoRate.HZ_60)  # Default to 60hz.
        save_settings(cabs, jams)

def save_settings(cabs, jams):
    print("Saving settings")
    f = open(CFG_FILENAME, 'w')
    for btn in cabs:
        state = btn.serialized_state()
        print("Save: " + state.strip())
        f.write(state)
    f.close()

def run():
    led = Pin(25, Pin.OUT)
    led.on()
    
    prog_btn = ProgramButton(0)
    cabs = (CabButton(1, "Cab1"), CabButton(2, "Cab2"), CabButton(3, "Cab3"), CabButton(4, "Cab4"))
    jams = (JammaButton(5, "Jamma1"), JammaButton(6, "Jamma2"), JammaButton(7, "Jamma3"), JammaButton(8, "Jamma4"))
    load_settings(cabs, jams)

    print("Starting main loop")
    last_tick = utime.ticks_us()
    while True:
        new_tick = utime.ticks_us()
        if utime.ticks_diff(new_tick, last_tick) < 16666: # ~60hz
            utime.sleep_us(100)
            continue
        last_tick = new_tick

        if prog_btn.pin.value() == 0: program(cabs, jams)
        for cab in cabs: cab.fire_if_pressed()
        for jam in jams: jam.maybe_fire()
        
print("Starting")
run()        
        
