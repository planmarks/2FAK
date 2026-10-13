/* 2FAK USB business-card demo
 * Standalone USB HID keyboard. On button press (SW1/PA0), "types" the sequence
 * to open a URL in the default browser, blinking the LED (D1/PB3) meanwhile.
 * Target host: Windows (Win+R). Own-device demo only.
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
#include "usbd_kbd.h"

/* ---- what to type ---- */
#define TARGET_URL   "https://instagram.com/papathought"

/* ---- board pins ---- */
#define LED_PORT   GPIOB
#define LED_PIN    LL_GPIO_PIN_3     /* D1, active high */
#define BTN_PORT   GPIOA
#define BTN_PIN    LL_GPIO_PIN_0     /* SW1, active low (pull-up) */

/* ---- HID keycodes ---- */
#define KEY_ENTER  0x28
#define MOD_LSHIFT 0x02
#define MOD_LGUI   0x08

USBD_HandleTypeDef usbd_dev;
extern PCD_HandleTypeDef hpcd;

static volatile uint32_t s_ms;

/* ---- minimal CMSIS system (we don't use Solo's system_stm32l4xx.c) ---- */
uint32_t SystemCoreClock = 4000000;   /* updated by LL_SetSystemCoreClock() */
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
  /* Button PA0: input, pull-up (pressed = low) */
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
static int  btn_down(void){ return (LL_GPIO_ReadInputPort(BTN_PORT) & BTN_PIN) == 0; }

/* map ASCII -> (modifier, keycode); returns 1 if typable */
static int ascii_to_key(char c, uint8_t *mod, uint8_t *key)
{
  *mod = 0; *key = 0;
  if (c >= 'a' && c <= 'z') { *key = 0x04 + (c - 'a'); return 1; }
  if (c >= 'A' && c <= 'Z') { *mod = MOD_LSHIFT; *key = 0x04 + (c - 'A'); return 1; }
  if (c >= '1' && c <= '9') { *key = 0x1E + (c - '1'); return 1; }
  switch (c) {
    case '0': *key = 0x27; return 1;
    case ' ': *key = 0x2C; return 1;
    case '-': *key = 0x2D; return 1;
    case '_': *mod = MOD_LSHIFT; *key = 0x2D; return 1;
    case '=': *key = 0x2E; return 1;
    case '+': *mod = MOD_LSHIFT; *key = 0x2E; return 1;
    case '.': *key = 0x37; return 1;
    case '/': *key = 0x38; return 1;
    case '?': *mod = MOD_LSHIFT; *key = 0x38; return 1;
    case ';': *key = 0x33; return 1;
    case ':': *mod = MOD_LSHIFT; *key = 0x33; return 1;
    case '@': *mod = MOD_LSHIFT; *key = 0x1F; return 1;
    case '#': *mod = MOD_LSHIFT; *key = 0x20; return 1;
    default:  return 0;
  }
}

static void send_report(uint8_t *rep)
{
  uint32_t t = HAL_GetTick();
  while (!USBD_KBD_IsIdle(&usbd_dev) && (HAL_GetTick() - t) < 50) { }
  USBD_KBD_SendReport(&usbd_dev, rep);
  t = HAL_GetTick();
  while (!USBD_KBD_IsIdle(&usbd_dev) && (HAL_GetTick() - t) < 50) { }
  HAL_Delay(6);
}

static void tap(uint8_t mod, uint8_t key)
{
  uint8_t rep[8] = {0};
  rep[0] = mod; rep[2] = key;
  send_report(rep);
  uint8_t rel[8] = {0};
  send_report(rel);
}

static void type_str(const char *s)
{
  for (; *s; s++) {
    uint8_t mod, key;
    if (ascii_to_key(*s, &mod, &key)) {
      tap(mod, key);
      /* blink while typing */
      if (LL_GPIO_IsOutputPinSet(LED_PORT, LED_PIN)) led_off(); else led_on();
    }
  }
}

static void open_url(void)
{
  led_on();
  tap(MOD_LGUI, 0x15);      /* Win + R -> Run dialog */
  HAL_Delay(700);
  type_str(TARGET_URL);
  HAL_Delay(80);
  tap(0, KEY_ENTER);        /* launch */
  /* success blink */
  for (int i = 0; i < 6; i++) { led_on(); HAL_Delay(80); led_off(); HAL_Delay(80); }
}

int main(void)
{
  SCB->VTOR = 0x08000000;   /* standalone: vector table at flash base */
  SystemClock_Config();
  SysTick_Config(SystemCoreClock / 1000);   /* 1 ms tick + IRQ */
  NVIC_SetPriority(SysTick_IRQn, 0);
  gpio_init();

  USBD_Init(&usbd_dev, &KBD_Desc, 0);
  USBD_RegisterClass(&usbd_dev, &USBD_KBD);
  USBD_Start(&usbd_dev);

  /* idle heartbeat until first press */
  uint32_t hb = HAL_GetTick();
  while (1) {
    if (usbd_dev.dev_state == USBD_STATE_CONFIGURED && btn_down()) {
      HAL_Delay(30);                 /* debounce */
      if (btn_down()) {
        open_url();
        while (btn_down()) { }       /* wait for release */
        HAL_Delay(200);
        led_off();
      }
    }
    /* slow heartbeat blink so you can see it's alive */
    if ((HAL_GetTick() - hb) > 1500) {
      hb = HAL_GetTick();
      led_on(); HAL_Delay(15); led_off();
    }
  }
}
