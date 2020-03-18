##
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

import sys
import math
import argparse
import struct
import enum

from openocd import OpenOcd

class Register(enum.IntEnum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    R8 = 8
    R9 = 9
    R10 = 10
    R11 = 11
    R12 = 12
    SP = 13
    LR = 14
    PC = 15
    PSR = 16

WORD_SIZE = 4

# Initial stack pointer (SP) value.
INITIAL_SP = 0x20000200

# Vector Table Offset Register (VTOR).
VTOR_ADDR = 0xe000ed08
# Interrupt Control and State Register (ICSR).
ICSR_ADDR = 0xe000ed04
# System Handler Control and State Register (SHCSR).
SHCSR_ADDR = 0xe000ed24
# NVIC Interrupt Set-Enable Registers (ISER).
NVIC_ISER0_ADDR = 0xe000e100
# NVIC Interrupt Set-Pending Registers (ISPR).
NVIC_ISPR0_ADDR = 0xe000e200
# Debug Exception and Monitor Control Register (DEMCR).
DEMCR_ADDR = 0xe000edfc
# Memory region with eXecute Never (XN) property.
MEM_XN_ADDR = 0xe0000000

SVC_INST_ADDR = 0x20000000
NOP_INST_ADDR = 0x20000002
LDR_INST_ADDR = 0x20000004
UNDEF_INST_ADDR = 0x20000006

# Inaccessible exception numbers.
INACCESSIBLE_EXC_NUMBERS = [0, 1, 7, 8, 9, 10, 13]

def generate_exception(openocd, vt_address, exception_number):
    openocd.send('reset halt')

    # Relocate vector table.
    openocd.write_memory(VTOR_ADDR, [vt_address])

    registers = dict()

    if exception_number == 2:
        # Generate a non-maskable interrupt.
        openocd.write_memory(ICSR_ADDR, [1 << 31])
        registers[Register.PC] = NOP_INST_ADDR
    elif exception_number == 3:
        # Generate a HardFault exception due to priority escalation.
        registers[Register.PC] = UNDEF_INST_ADDR
    elif exception_number == 4:
        # Generate a MemFault exception by executing memory with
        # eXecute-Never (XN) property.
        registers[Register.PC] = MEM_XN_ADDR
        # Enable MemFault exceptions.
        openocd.write_memory(SHCSR_ADDR, [0x10000])
    elif exception_number == 5:
        # Generate a BusFault exception by executing a load instruction that
        # accesses invalid memory.
        registers[Register.PC] = LDR_INST_ADDR
        # Enable BusFault exceptions.
        openocd.write_memory(SHCSR_ADDR, [0x20000])
        registers[Register.R6] = 0xffffff00
    elif exception_number == 6:
        # Generate an UsageFault by executing an undefined instruction.
        registers[Register.PC] = UNDEF_INST_ADDR
        # Enable UsageFault exceptions.
        openocd.write_memory(SHCSR_ADDR, [0x40000])
    elif exception_number == 11:
        # Generate a Supervisor Call (SVCall) exception.
        registers[Register.PC] = SVC_INST_ADDR
    elif exception_number == 12:
        # Generate a DebugMonitor exception.
        registers[Register.PC] = NOP_INST_ADDR
        openocd.write_memory(DEMCR_ADDR, [1 << 17])
    elif exception_number == 14:
        # Generate a PendSV interrupt.
        openocd.write_memory(ICSR_ADDR, [1 << 28])
        registers[Register.PC] = NOP_INST_ADDR
    elif exception_number == 15:
        # Generate a SysTick interrupt.
        openocd.write_memory(ICSR_ADDR, [1 << 26])
        registers[Register.PC] = NOP_INST_ADDR
    elif exception_number >= 16:
        # Generate an external interrupt.
        ext_interrupt_number = exception_number - 16

        register_offset = (ext_interrupt_number // 32) * WORD_SIZE
        value = (1 << (ext_interrupt_number % 32))

        # Enable and make interrupt pending.
        openocd.write_memory(NVIC_ISER0_ADDR + register_offset, [value])
        openocd.write_memory(NVIC_ISPR0_ADDR + register_offset, [value])

        registers[Register.PC] = NOP_INST_ADDR
    else:
        sys.exit('Exception number %u not handled' % exception_number)

    # Ensure that the processor operates in Thumb mode.
    registers[Register.PSR] = 0x01000000
    registers[Register.SP] = INITIAL_SP

    for reg in registers:
        openocd.write_register(reg, registers[reg])

    # Perform a single step to generate the exception.
    openocd.send('step')

def recover_pc(openocd):
    (pc, xpsr) = openocd.read_register_list([Register.PC, Register.PSR])

    # Recover LSB of the PC from the EPSR.T bit.
    t_bit = (xpsr >> 24) & 0x1

    return pc | t_bit

def align(address, base):
    return address - (address % base)

def determine_num_ext_interrupts(openocd):
    count = 0

    # The ARMv7-M architecture supports up to 496 external interrupts.
    for i in range(0, 496):
        openocd.send('reset init')

        register_offset = (i // 32) * WORD_SIZE
        value = (1 << (i % 32))

        # Enable and make interrupt pending.
        openocd.write_memory(NVIC_ISER0_ADDR + register_offset, [value])
        openocd.write_memory(NVIC_ISPR0_ADDR + register_offset, [value])

        openocd.write_register(Register.PC, NOP_INST_ADDR)
        # Ensure that the processor operates in Thumb mode.
        openocd.write_register(Register.PSR, 0x01000000)
        openocd.write_register(Register.SP, INITIAL_SP)

        openocd.step()
        xpsr = openocd.read_register(Register.PSR)
        exception_number = xpsr & 0x1ff

        if exception_number != (i + 16):
            break

        count += 1

    return count

def calculate_vtor_exc(address, num_exceptions):
    # The vector table size must be a power of two.
    table_size = 2 ** int(math.log(num_exceptions, 2))
    vtor_address = align(address, table_size * WORD_SIZE)

    exception_number = (address - vtor_address) // WORD_SIZE

    if exception_number not in INACCESSIBLE_EXC_NUMBERS:
        return (vtor_address, exception_number)

    # Use the wrap-around behaviour to generate an exception for an
    # inaccessible vector table entry.
    # This is only possible when the vector table is not aligned to its size
    # and the device has enough exceptions.
    if (vtor_address % (table_size * 2 * WORD_SIZE)) != 0 \
            and (exception_number + table_size) < num_exceptions:
        exception_number += table_size

    return (vtor_address, exception_number)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('address', help='Extraction start address')
    parser.add_argument('length', help='Number of words to extract')
    parser.add_argument('--value', default='0xffffffff',
        help=('Value to be used for non-extractable memory words. '
              'Use "skip" to ignore them'))
    parser.add_argument('--binary', action='store_true',
        help='Output binary')
    parser.add_argument('--host', default='localhost',
        help='OpenOCD Tcl interface host')
    parser.add_argument('--port', type=int, default=6666,
        help='OpenOCD Tcl interface port')
    args = parser.parse_args()

    start_address = int(args.address, 0)
    length = int(args.length, 0)
    skip_value = args.value
    binary_output = args.binary

    if skip_value != 'skip':
        skip_value = int(skip_value, 0)

    oocd = OpenOcd(args.host, args.port)

    try:
        oocd.connect()
    except Exception as e:
        sys.exit('Failed to connect to OpenOCD')

    # Disable exception masking by OpenOCD. The target must be halted before
    # the masking behaviour can be changed.
    oocd.halt()
    oocd.send('cortex_m maskisr off')

    # Write 'svc #0', 'nop', 'ldr r0, [r1, #0]' and an undefined instruction
    # to the SRAM. We use them later to generate exceptions.
    oocd.write_memory(SVC_INST_ADDR, [0xdf00], word_length=16)
    oocd.write_memory(NOP_INST_ADDR, [0xbf00], word_length=16)
    oocd.write_memory(LDR_INST_ADDR, [0x7b75], word_length=16)
    oocd.write_memory(UNDEF_INST_ADDR, [0xffff], word_length=16)

    num_exceptions = 16 + determine_num_ext_interrupts(oocd)
    end_address = start_address + (length * WORD_SIZE)

    for address in range(start_address, end_address, WORD_SIZE):
        (vtor_address, exception_number) = calculate_vtor_exc(
            address, num_exceptions)

        if address == 0x00000000:
            oocd.send('reset halt')
            recovered_value = oocd.read_register(Register.SP)
        elif address == 0x00000004:
            oocd.send('reset halt')
            recovered_value = recover_pc(oocd)
        elif exception_number in INACCESSIBLE_EXC_NUMBERS:
            recovered_value = None
        else:
            generate_exception(oocd, vtor_address, exception_number)
            recovered_value = recover_pc(oocd)

        if recovered_value is None and skip_value == 'skip':
            continue

        if recovered_value is None:
            recovered_value = skip_value

        if binary_output:
            output_value = struct.pack('<I', recovered_value)
            sys.stdout.buffer.write(output_value)
        else:
            output_value = '%08x: %08x\n' % (address, recovered_value)
            sys.stdout.write(output_value)

        sys.stdout.flush()
