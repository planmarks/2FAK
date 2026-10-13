/* 2FAK Mouse Jiggler
 * Standalone USB HID mouse. While plugged into a computer, it nudges the
 * pointer a few pixels (and immediately back) at a random interval between
 * 1 and 23 seconds, keeping the host awake. The LED (D1/PB3) blinks on each
 * jiggle, with a slow heartbeat in between. Runs automatically on plug-in.
 */
#include "stm32l4xx_hal.h"
#include "stm32l4xx_ll_rcc.h"
#include "stm32l4xx_ll_bus.h"
#include "stm32l4xx_ll_system.h"
#include "stm32l4xx_ll_utils.h"
#include "stm32l4xx_ll_pwr.h"
#include "stm32l4xx_ll_gpio.h"
#include "stm32l4xx_ll_crs.h"
#include "stm32l4xx_ll_cortex.h"

#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_mouse.h"

/* ---- jiggle tuning ---- */
#define JIGGLE_MIN_S   1U      /* shortest interval, seconds */
#define JIGGLE_MAX_S   23U     /* longest interval, seconds  */
#define JIGGLE_MIN_PX  3       /* smallest nudge, pixels     */
#define JIGGLE_SPAN_PX 8       /* nudge = MIN..(MIN+SPAN-1)  */

/* ---- board pins ---- */
#define LED_PORT   GPIOB
#define LED_PIN    LL_GPIO_PIN_3     /* D1, active high */
#define BTN_PORT   GPIOA
#define BTN_PIN    LL_GPIO_PIN_0     /* SW1, active low (pull-up) - unused, free to extend */

USBD_HandleTypeDef usbd_dev;
extern PCD_HandleTypeDef hpcd;

static volatile uint32_t s_ms;

/* ---- minimal CMSIS system ---- */
uint32_t SystemCoreClock = 4000000;
void SystemInit(void)
{
#if (defined(__FPU_PRESENT) && (__FPU_PRESENT == 1U)) && (defined(__FPU_USED) && (__FPU_USED == 1U))
  SCB->CPACR |= ((3UL << 20U) | (3UL << 22U));   /* enable CP10/CP11 (FPU) */
#endif
  SCB->VTOR = 0x08000000;
}

/* ---- HAL tick (SysTick) ---- */
uint32_t HAL_GetTick(void) { return s_ms; }
void HAL_Delay(uint32_t ms) { uint32_t t = s_ms; while ((s_ms - t) < ms) { __NOP(); } }
void SysTick_Handler(void) { s_ms++; }
void USB_IRQHandler(void) { HAL_PCD_IRQHandler(&hpcd); }

void Error_Handler(void) { while (1) { } }

/* ---- clock: MSI 48 MHz sysclk + HSI48/CRS for USB (from 2FAK build) ---- */
void SystemClock_Config(void)
{
  SET_BIT(RCC->APB1ENR1, RCC_APB1ENR1_PWREN);
  LL_FLASH_SetLatency(LL_FLASH_LATENCY_2);
  if (LL_FLASH_GetLatency() != LL_FLASH_LATENCY_2) Error_Handler();
  LL_PWR_SetRegulVoltageScaling(LL_PWR_REGU_VOLTAGE_SCALE1);

  LL_RCC_HSI48_Enable();
  while (LL_RCC_HSI48_IsReady() != 1) { }
  LL_RCC_MSI_Enable();
  while (LL_RCC_MSI_IsReady() != 1) { }
  LL_RCC_MSI_EnableRangeSelection();
  LL_RCC_MSI_SetRange(LL_RCC_MSIRANGE_11);   /* 48 MHz */
  LL_RCC_MSI_SetCalibTrimming(0);
  LL_RCC_SetSysClkSource(LL_RCC_SYS_CLKSOURCE_MSI);
  while (LL_RCC_GetSysClkSource() != LL_RCC_SYS_CLKSOURCE_STATUS_MSI) { }
  LL_RCC_SetAHBPrescaler(LL_RCC_SYSCLK_DIV_1);
  LL_RCC_SetAPB1Prescaler(LL_RCC_APB1_DIV_1);
  LL_RCC_SetAPB2Prescaler(LL_RCC_APB2_DIV_1);
  LL_Init1msTick(48000000);
  LL_SYSTICK_SetClkSource(LL_SYSTICK_CLKSOURCE_HCLK);
  LL_SetSystemCoreClock(48000000);

  LL_RCC_SetUSBClockSource(LL_RCC_USB_CLKSOURCE_HSI48);
  LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_CRS);
  LL_APB1_GRP1_ForceReset(LL_APB1_GRP1_PERIPH_CRS);
  LL_APB1_GRP1_ReleaseReset(LL_APB1_GRP1_PERIPH_CRS);
  LL_CRS_SetSyncDivider(LL_CRS_SYNC_DIV_1);
  LL_CRS_SetSyncPolarity(LL_CRS_SYNC_POLARITY_RISING);
  LL_CRS_SetSyncSignalSource(LL_CRS_SYNC_SOURCE_USB);
  LL_CRS_SetReloadCounter(__LL_CRS_CALC_CALCULATE_RELOADVALUE(48000000, 1000));
  LL_CRS_SetFreqErrorLimit(34);
  LL_CRS_SetHSI48SmoothTrimming(32);
}

static void gpio_init(void)
{
  LL_AHB2_GRP1_EnableClock(LL_AHB2_GRP1_PERIPH_GPIOA);
  LL_AHB2_GRP1_EnableClock(LL_AHB2_GRP1_PERIPH_GPIOB);
  /* Button PA0: input, pull-up (unused for now) */
  LL_GPIO_SetPinMode(BTN_PORT, BTN_PIN, LL_GPIO_MODE_INPUT);
  LL_GPIO_SetPinPull(BTN_PORT, BTN_PIN, LL_GPIO_PULL_UP);
  /* LED PB3: output push-pull */
  LL_GPIO_SetPinMode(LED_PORT, LED_PIN, LL_GPIO_MODE_OUTPUT);
  LL_GPIO_SetPinOutputType(LED_PORT, LED_PIN, LL_GPIO_OUTPUT_PUSHPULL);
  LL_GPIO_SetPinSpeed(LED_PORT, LED_PIN, LL_GPIO_SPEED_FREQ_LOW);
  LL_GPIO_SetPinPull(LED_PORT, LED_PIN, LL_GPIO_PULL_NO);
  LL_GPIO_ResetOutputPin(LED_PORT, LED_PIN);
}

static void led_on(void)  { LL_GPIO_SetOutputPin(LED_PORT, LED_PIN); }
static void led_off(void) { LL_GPIO_ResetOutputPin(LED_PORT, LED_PIN); }

/* ---- xorshift32 PRNG, seeded from the 96-bit device unique ID ---- */
static uint32_t rng_state;
static void rng_seed(void)
{
  const uint32_t *uid = (const uint32_t *)0x1FFF7590U;  /* STM32L4 UID base */
  uint32_t s = uid[0] ^ uid[1] ^ uid[2] ^ 0x9E3779B9U;
  rng_state = s ? s : 0xA5A5A5A5U;                       /* never zero */
}
static uint32_t rng_next(void)
{
  uint32_t x = rng_state;
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  rng_state = x;
  return x;
}

/* random interval in ms, JIGGLE_MIN_S .. JIGGLE_MAX_S seconds */
static uint32_t next_interval_ms(void)
{
  uint32_t span = (JIGGLE_MAX_S - JIGGLE_MIN_S) + 1U;    /* 23 possibilities */
  return 1000U * (JIGGLE_MIN_S + (rng_next() % span));
}

/* ---- send one 4-byte mouse report, bounded-wait like the kbd demo ---- */
static void mouse_send(int8_t dx, int8_t dy, int8_t wheel)
{
  uint8_t rep[4] = { 0x00, (uint8_t)dx, (uint8_t)dy, (uint8_t)wheel };
  uint32_t t = HAL_GetTick();
  while (!USBD_MOUSE_IsIdle(&usbd_dev) && (HAL_GetTick() - t) < 50) { }
  USBD_MOUSE_SendReport(&usbd_dev, rep);
  t = HAL_GetTick();
  while (!USBD_MOUSE_IsIdle(&usbd_dev) && (HAL_GetTick() - t) < 50) { }
}

/* Nudge the pointer a small random amount, then move it straight back so the
 * cursor doesn't drift over time. Blinks the LED for visible feedback. */
static void jiggle(void)
{
  int step = JIGGLE_MIN_PX + (int)(rng_next() % JIGGLE_SPAN_PX);   /* 3..10 */
  if (rng_next() & 1U) step = -step;

  led_on();
  mouse_send((int8_t)step, 0, 0);
  HAL_Delay(60);
  mouse_send((int8_t)(-step), 0, 0);
  led_off();
}

int main(void)
{
  SCB->VTOR = 0x08000000;   /* standalone: vector table at flash base */
  SystemClock_Config();
  SysTick_Config(SystemCoreClock / 1000);   /* 1 ms tick + IRQ */
  NVIC_SetPriority(SysTick_IRQn, 0);
  gpio_init();
  rng_seed();

  USBD_Init(&usbd_dev, &MOUSE_Desc, 0);
  USBD_RegisterClass(&usbd_dev, &USBD_MOUSE);
  USBD_Start(&usbd_dev);

  uint32_t hb        = HAL_GetTick();   /* heartbeat timer          */
  uint32_t next      = 0;               /* time of the next jiggle  */
  int      scheduled = 0;               /* is `next` valid?         */

  while (1) {
    int configured = (usbd_dev.dev_state == USBD_STATE_CONFIGURED);

    if (configured) {
      /* On first enumeration (or after a re-plug), arm the first interval. */
      if (!scheduled) {
        next = HAL_GetTick() + next_interval_ms();
        scheduled = 1;
      }
      if ((int32_t)(HAL_GetTick() - next) >= 0) {
        jiggle();
        next = HAL_GetTick() + next_interval_ms();
      }
    } else {
      scheduled = 0;   /* unplugged/suspended: re-arm cleanly on reconnect */
    }

    /* slow heartbeat blink so you can see it's alive */
    if ((HAL_GetTick() - hb) > 2000) {
      hb = HAL_GetTick();
      led_on(); HAL_Delay(12); led_off();
    }
  }
}
