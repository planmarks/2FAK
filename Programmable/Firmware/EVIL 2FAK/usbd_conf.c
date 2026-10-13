/* 2FAK USB business-card demo - USB device low-level (PCD) glue, keyboard only */
#include "stm32l4xx_ll_gpio.h"
#include "stm32l4xx_ll_usb.h"
#include "stm32l4xx_hal_pcd.h"
#include "stm32l4xx_hal.h"
#include "usbd_core.h"
#include "usbd_conf.h"

PCD_HandleTypeDef hpcd;
void Error_Handler(void);

/* ---- MSP ---- */
void HAL_PCD_MspInit(PCD_HandleTypeDef *h) {
  SET_BIT(RCC->APB1ENR1, RCC_APB1ENR1_USBFSEN);
  NVIC_SetPriority(USB_IRQn, NVIC_EncodePriority(NVIC_GetPriorityGrouping(), 0x0f, 0));
  NVIC_EnableIRQ(USB_IRQn);
}
void HAL_PCD_MspDeInit(PCD_HandleTypeDef *h) {
  CLEAR_BIT(RCC->APB1ENR1, RCC_APB1ENR1_USBFSEN);
}

/* ---- PCD -> USBD library callbacks ---- */
void HAL_PCD_SetupStageCallback(PCD_HandleTypeDef *h) {
  USBD_LL_SetupStage((USBD_HandleTypeDef *)h->pData, (uint8_t *)h->Setup);
}
void HAL_PCD_DataOutStageCallback(PCD_HandleTypeDef *h, uint8_t epnum) {
  USBD_LL_DataOutStage((USBD_HandleTypeDef *)h->pData, epnum, h->OUT_ep[epnum].xfer_buff);
}
void HAL_PCD_DataInStageCallback(PCD_HandleTypeDef *h, uint8_t epnum) {
  USBD_LL_DataInStage((USBD_HandleTypeDef *)h->pData, epnum, h->IN_ep[epnum].xfer_buff);
}
void HAL_PCD_SOFCallback(PCD_HandleTypeDef *h) { USBD_LL_SOF((USBD_HandleTypeDef *)h->pData); }
void HAL_PCD_ResetCallback(PCD_HandleTypeDef *h) {
  USBD_LL_SetSpeed((USBD_HandleTypeDef *)h->pData, USBD_SPEED_FULL);
  USBD_LL_Reset((USBD_HandleTypeDef *)h->pData);
}
void HAL_PCD_SuspendCallback(PCD_HandleTypeDef *h) { (void)h; }
void HAL_PCD_ResumeCallback(PCD_HandleTypeDef *h) { (void)h; }
void HAL_PCD_ISOOUTIncompleteCallback(PCD_HandleTypeDef *h, uint8_t e) { USBD_LL_IsoOUTIncomplete((USBD_HandleTypeDef *)h->pData, e); }
void HAL_PCD_ISOINIncompleteCallback(PCD_HandleTypeDef *h, uint8_t e) { USBD_LL_IsoINIncomplete((USBD_HandleTypeDef *)h->pData, e); }
void HAL_PCD_ConnectCallback(PCD_HandleTypeDef *h) { USBD_LL_DevConnected((USBD_HandleTypeDef *)h->pData); }
void HAL_PCD_DisconnectCallback(PCD_HandleTypeDef *h) { USBD_LL_DevDisconnected((USBD_HandleTypeDef *)h->pData); }

/* ---- USBD library -> LL driver ---- */
USBD_StatusTypeDef USBD_LL_Init(USBD_HandleTypeDef *pdev) {
  SET_BIT(PWR->CR2, PWR_CR2_USV);           /* enable USB supply */
  hpcd.pData = pdev;
  pdev->pData = &hpcd;
  hpcd.Instance = USB;
  hpcd.Init.dev_endpoints = 8;
  hpcd.Init.speed = PCD_SPEED_FULL;
  hpcd.Init.ep0_mps = DEP0CTL_MPS_64;
  hpcd.Init.phy_itface = PCD_PHY_EMBEDDED;
  hpcd.Init.Sof_enable = DISABLE;
  hpcd.Init.low_power_enable = DISABLE;
  hpcd.Init.lpm_enable = DISABLE;
  hpcd.Init.battery_charging_enable = DISABLE;
  if (HAL_PCD_Init(&hpcd) != HAL_OK) { Error_Handler(); }
  HAL_PCDEx_PMAConfig(&hpcd, 0x00, PCD_SNG_BUF, 0x18);        /* EP0 OUT */
  HAL_PCDEx_PMAConfig(&hpcd, 0x80, PCD_SNG_BUF, 0x58);        /* EP0 IN */
  HAL_PCDEx_PMAConfig(&hpcd, KBD_EPIN_ADDR, PCD_SNG_BUF, 0x98); /* KBD IN */
  return USBD_OK;
}
USBD_StatusTypeDef USBD_LL_DeInit(USBD_HandleTypeDef *pdev) { HAL_PCD_DeInit((PCD_HandleTypeDef *)pdev->pData); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_Start(USBD_HandleTypeDef *pdev) { HAL_PCD_Start((PCD_HandleTypeDef *)pdev->pData); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_Stop(USBD_HandleTypeDef *pdev) { HAL_PCD_Stop((PCD_HandleTypeDef *)pdev->pData); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_OpenEP(USBD_HandleTypeDef *pdev, uint8_t a, uint8_t t, uint16_t m) { HAL_PCD_EP_Open((PCD_HandleTypeDef *)pdev->pData, a, m, t); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_CloseEP(USBD_HandleTypeDef *pdev, uint8_t a) { HAL_PCD_EP_Close((PCD_HandleTypeDef *)pdev->pData, a); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_FlushEP(USBD_HandleTypeDef *pdev, uint8_t a) { HAL_PCD_EP_Flush((PCD_HandleTypeDef *)pdev->pData, a); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_StallEP(USBD_HandleTypeDef *pdev, uint8_t a) { HAL_PCD_EP_SetStall((PCD_HandleTypeDef *)pdev->pData, a); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_ClearStallEP(USBD_HandleTypeDef *pdev, uint8_t a) { HAL_PCD_EP_ClrStall((PCD_HandleTypeDef *)pdev->pData, a); return USBD_OK; }
uint8_t USBD_LL_IsStallEP(USBD_HandleTypeDef *pdev, uint8_t a) {
  PCD_HandleTypeDef *h = (PCD_HandleTypeDef *)pdev->pData;
  return (a & 0x80) ? h->IN_ep[a & 0x7F].is_stall : h->OUT_ep[a & 0x7F].is_stall;
}
USBD_StatusTypeDef USBD_LL_SetUSBAddress(USBD_HandleTypeDef *pdev, uint8_t addr) { HAL_PCD_SetAddress((PCD_HandleTypeDef *)pdev->pData, addr); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_Transmit(USBD_HandleTypeDef *pdev, uint8_t a, uint8_t *b, uint16_t s) { HAL_PCD_EP_Transmit((PCD_HandleTypeDef *)pdev->pData, a, b, s); return USBD_OK; }
USBD_StatusTypeDef USBD_LL_PrepareReceive(USBD_HandleTypeDef *pdev, uint8_t a, uint8_t *b, uint16_t s) { HAL_PCD_EP_Receive((PCD_HandleTypeDef *)pdev->pData, a, b, s); return USBD_OK; }
uint32_t USBD_LL_GetRxDataSize(USBD_HandleTypeDef *pdev, uint8_t a) { return HAL_PCD_EP_GetRxCount((PCD_HandleTypeDef *)pdev->pData, a); }
void USBD_LL_Delay(uint32_t d) { HAL_Delay(d); }
