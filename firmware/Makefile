##
## Copyright (C) 2020 Marc Schink <dev@zapb.de>
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

PREFIX ?= arm-none-eabi-
CC = $(PREFIX)gcc
OBJCOPY = $(PREFIX)objcopy

OPENOCD ?= openocd

FP_FLAGS = -msoft-float
ARCH_FLAGS = -mcpu=cortex-m3 -mthumb $(FP_FLAGS)

LD_SCRIPT = libopencm3/lib/stm32/f1/stm32f100xb.ld

LDFLAGS = -L./libopencm3/lib
LDFLAGS += --static -nostartfiles
LDFLAGS += -T$(LD_SCRIPT)

CFLAGS = $(ARCH_FLAGS)
CFLAGS += -std=c11 -g3 -O0
CFLAGS += -I./libopencm3/include
CFLAGS += -fno-common -ffunction-sections -fdata-sections
CFLAGS += -DSTM32F1

LDLIBS = -Wl,--start-group -lc -lgcc -lnosys -Wl,--end-group
LDLIBS += -lopencm3_stm32f1

FIRMWARE_ELF = firmware.elf
FIRMWARE_BIN = firmware.bin
FIRMWARE_HEX = firmware.hex

all: $(FIRMWARE_ELF) $(FIRMWARE_BIN) $(FIRMWARE_HEX)

$(FIRMWARE_ELF): main.c libopencm3/lib/libopencm3_stm32f1.a
	$(CC) $(CFLAGS) $(LDFLAGS) main.c $(LDLIBS) -o firmware.elf

libopencm3/Makefile:
	git submodule update --init

libopencm3/lib/libopencm3_%.a: libopencm3/Makefile
	$(MAKE) -C libopencm3 TARGETS=stm32/f1

$(FIRMWARE_BIN): $(FIRMWARE_ELF)
	$(OBJCOPY) -O binary $< $@

$(FIRMWARE_HEX): $(FIRMWARE_ELF)
	$(OBJCOPY) -O ihex $< $@

flash: $(FIRMWARE_ELF)
	$(OPENOCD) -f interface/jlink.cfg -c "transport select swd" -f target/stm32f1x.cfg -c "program $(FIRMWARE_ELF) verify reset exit"

clean:
	$(RM) $(FIRMWARE_ELF) $(FIRMWARE_BIN) $(FIRMWARE_HEX)

distclean: clean
	$(MAKE) -C libopencm3 clean

.PHONY: all flash clean distclean
