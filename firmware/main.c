/*
 * Copyright (C) 2020 Marc Schink <dev@zapb.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdbool.h>

#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>

#define LED2_GPIO	GPIOA
#define LED2_PIN	GPIO5

char *text = "This is some secret data stored in the flash memory together with the firmware. Exception(al) failure...!";

int main(void)
{
	rcc_periph_clock_enable(RCC_GPIOA);

	gpio_set_mode(LED2_GPIO, GPIO_MODE_OUTPUT_2_MHZ,
		GPIO_CNF_OUTPUT_PUSHPULL, LED2_PIN);
	gpio_clear(LED2_GPIO, LED2_PIN);

	while (true) {
		for (uint32_t i = 0; i < (1 << 18); i++) {
			__asm__("nop");
		}

		gpio_toggle(LED2_GPIO, LED2_PIN);
	}
}
