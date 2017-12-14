import argparse
import textwrap

try:
    from vcd import VCDWriter
except ImportError:
    print("Could not find the vcd modules, either import pyvcd with pypi")
    print("or copy locally the vcd module from pyvcd repository")
    raise

# use a customer formatter to do raw text and add default values
class CustomerFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass

parser = argparse.ArgumentParser(formatter_class=CustomerFormatter,
                                 description=textwrap.dedent('''
    Generate a VCD file containing JTAG transactions
    '''))

parser.add_argument('outfile', action='store', type=argparse.FileType('w'),
    help='path to the VCD file to create')

my_args = parser.parse_args()

with VCDWriter(my_args.outfile, timescale='1 ns', date='today') as writer:
    tck_v = writer.register_var('capture', 'tck', 'wire', size=1, init=0)
    tms_v = writer.register_var('capture', 'tms', 'wire', size=1, init=0)
    tdi_v = writer.register_var('capture', 'tdi', 'wire', size=1, init=0)
    tdo_v = writer.register_var('capture', 'tdo', 'wire', size=1, init=0)

    step = 0

    def clock_signal(signal, step, value):
        writer.change(tck_v, step, 0)
        writer.change(signal, step, value)
        step += 1
        writer.change(tck_v, step, 1)
        step += 1
        return step

    def clock_signals(signals, step, values):
        writer.change(tck_v, step, 0)
        for i, s in enumerate(signals):
            writer.change(s, step, values[i])
        step += 1
        writer.change(tck_v, step, 1)
        step += 1
        return step

    def tms(step, values):
        "s is the current step, v is the list of values"
        if len(values) != 0:
            writer.change(tdi_v, step, 0)

        for v in values:
            step = clock_signal(tms_v, step, v)
        return step
        
    def tdi(step, values):
        "s is the current step, v is the list of values"
        assert len(values) != 0, "An empty list of values was passed as parameter"

        # first step => clear TMS
        writer.change(tms_v, step, 0)
        
        for v in values[:-1]:
            step = clock_signal(tdi_v, step, v)

        # last step => set TMS
        step = clock_signals([tdi_v, tms_v], step, [values[-1], 1])
        return step
    
    def tdo(step, values):
        "s is the current step, v is the list of values"
        assert(len(values) != 0)
        
        # first step => clear TMS
        writer.change(tms_v, step, 0)
            
        for v in values[:-1]:
            step = clock_signal(tdo_v, step, v)

        # last step => set TMS
        step = clock_signals([tdo_v, tms_v], step, [values[-1], 1])
        return step

    # go to reset mode and directly to run test idle (5 ones should be enough)
    step = tms(step, "1"*5 + "0")
    # go to shift instruction
    step = tms(step, "1100")
    # send instruction IDCODE = 4
    step = tdi(step, '{0:08b}'.format(4))
    # go to shift data
    step = tms(step, "1100")
    # read out IDCODE
    step = tdo(step, '{0:032b}'.format(0x15A083))
    # go to test idle
    step = tms(step, "10")
    

my_args.outfile.close()


