##
## OpenOCD remote procedure call (RPC) library.
##
## Copyright (C) 2014 Andreas Ortmann <ortmann@finf.uni-hannover.de>
## Copyright (C) 2019 Marc Schink <dev@zapb.de>
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

import telnetlib

class OpenOcd:

    def __init__(self, host='localhost', port=4444):
        self.tn = telnetlib.Telnet(host, port)
        #write_raw_sequence(self.tn, telnetlib.IAC + telnetlib.WILL + telnetlib.ECHO)
        self.Readout()

        self._tcl_variable = 'python_tcl'

    def Readout(self):
        s = ''
        Lines = []
        while True:
            s += self.tn.read_some().decode('utf8')
            l = s.splitlines()
            if len(l) > 1:
                for s in l[:-1]:
                    if len(s) > 0:
                        Lines.append(s)
                s = l[-1]
            if s == '> ':
                return Lines

    def send(self, Cmd, *args):
        Text = Cmd
        for arg in args:
            if arg:
                Text += ' ' + arg
        Text += '\n'
        self.tn.write(Text.encode('utf8'))
        return self.Readout()[-1]

    def exit(self):
        self.send('exit')

    def step(self):
        self.send('step')

    def resume(self, address=None):
        if address is None:
            self.send('resume')
        else:
            self.send('resume 0x%x' % address)

    def halt(self):
        self.send('halt')

    def wait_halt(self, timeout=5000):
        self.send('wait_halt %u' % timeout)

    def write_memory(self, address, data, word_length=32):
        array = ' '.join(['%d 0x%x' % (i, v) for (i, v) in enumerate(data)])

        # Clear the array before using it.
        self.send('array unset %s' % self._tcl_variable)

        self.send('array set %s { %s }' % (self._tcl_variable, array))
        self.send('array2mem %s 0x%x %s %d' % (self._tcl_variable,
            word_length, address, len(data)))

    def read_memory(self, address, count, word_length=32):
        # Clear the array before using it.
        self.send('array unset %s' % self._tcl_variable)

        self.send('mem2array %s %d 0x%x %d' % (self._tcl_variable,
            word_length, address, count))

        raw = self.send('return $%s' % self._tcl_variable).split(' ')

        order = [int(raw[2 * i]) for i in range(len(raw) // 2)]
        values = [int(raw[2 * i + 1]) for i in range(len(raw) // 2)]

        # Sort the array because it may not be sorted by the memory address.
        result = [0] * len(values)
        for (i, pos) in enumerate(order):
            result[pos] = values[i]

        return result

    def read_register(self, register):
        if issubclass(type(register), int):
            raw = self.send('reg %u' % register).split(': ')
        else:
            raw = self.send('reg %s' % register).split(': ')

        if len(raw) < 2:
            return None

        return int(raw[1], 16)

    def read_registers(self, registers):
        result = dict()

        for register in registers:
            value = self.read_register(register)

            if value is None:
                return None

            result[register] = value

        return result

    def read_register_list(self, registers):
        register_list = [None] * len(registers)
        result = self.read_registers(registers)

        # Preserve register order.
        for reg in result:
            register_list[registers.index(reg)] = result[reg]

        return register_list

    def write_register(self, register, value):
        if issubclass(type(register), int):
            self.send('reg %u 0x%x' % (register, value))
        else:
            self.send('reg %s 0x%x' % (register, value))

    def write_registers(self, registers):
        for reg in registers:
            self.write_register(reg, registers[reg])

    def set_breakpoint(self, address, length=2, hardware=True):
        if hardware:
            self.send('bp 0x%x %u hw' % (address, length))
        else:
            self.send('bp 0x%x %u' % (address, length))

    def remove_breakpoint(self):
        self.send('rbp 0x%x' % address)
