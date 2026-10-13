# RoHS Compliance – 2FAK

| | |
|---|---|
| **Document** | RoHS Declaration of Conformity and Compliance File |
| **Product** | 2FAK |
| **Model / BOM reference** | `2FAK V1A/V1B/V1C`  |
| **Hardware revision** | `V1A`, `V1B`, `V1C` |
| **Document revision** | 1 |
| **Date** | 2026-10-03 |

---

## 1. Product identification

| | |
|---|---|
| Product name | 2FAK |
| Product description | USB-powered device built on an STM32L432 microcontroller with an ATECC608B secure element (hardware security / two-factor authentication key). |
| Manufacturer (legal entity) | `Muru Global OU` |
| Address | `Tondi 8a, Tallinn, 11313, Harju county, Estonia` |
| Contact | `info@muru.global` |
| Proposed RoHS category (Annex I) | Category 3 – IT and telecommunications equipment  |
| Identification on product | `V1A`, `V1B`, `V1C` |

## 2. Declaration of Conformity (RoHS)

> We, `Muru Global OU`, `Tondi 8a, Tallinn, 11313, Harju county, Estonia`, declare under our sole responsibility that the product
>
> **2FAK** – hardware revisions `V1A`, `V1B`, `V1C`
>
> to which this declaration relates is in conformity with **Directive 2011/65/EU** of the European Parliament and of the Council of 8 June 2011 on the restriction of the use of certain hazardous substances in electrical and electronic equipment (RoHS), as amended by **Commission Delegated Directive (EU) 2015/863** (RoHS 3).
>
> The product does not contain any of the restricted substances listed in Annex II above the maximum concentration values given below, except for applications exempted under Annex III or Annex IV of the Directive as documented in the technical file.
>
> The technical documentation was prepared in accordance with the harmonised standard **EN IEC 63000:2018** – *Technical documentation for the assessment of electrical and electronic products with respect to the restriction of hazardous substances*.
>
> Place and date of issue: `Tallinn`, `[2026-10-06]`
>
> Signed for and on behalf of `Muru Global`:
>
> Name: `[name]` &nbsp;&nbsp; Function: `[function]` &nbsp;&nbsp; Signature: ____________________

### Restricted substances (Annex II, as amended by (EU) 2015/863)

| Substance | Max. concentration (by weight in homogeneous material) |
|---|---|
| Lead (Pb) | 0.1 % (1000 ppm) |
| Mercury (Hg) | 0.1 % (1000 ppm) |
| Cadmium (Cd) | 0.01 % (100 ppm) |
| Hexavalent chromium (Cr VI) | 0.1 % (1000 ppm) |
| Polybrominated biphenyls (PBB) | 0.1 % (1000 ppm) |
| Polybrominated diphenyl ethers (PBDE) | 0.1 % (1000 ppm) |
| Bis(2-ethylhexyl) phthalate (DEHP) | 0.1 % (1000 ppm) |
| Butyl benzyl phthalate (BBP) | 0.1 % (1000 ppm) |
| Dibutyl phthalate (DBP) | 0.1 % (1000 ppm) |
| Diisobutyl phthalate (DIBP) | 0.1 % (1000 ppm) |

### Exemptions (Annex III)

No device-level exemption is claimed. Some supplier declarations may rely on Annex III exemptions. These are typically **7(c)-I**, lead in glass or ceramic of thick-film resistors and ceramic capacitors, and **6(c)**, lead in copper alloys of connectors. Each exemption a supplier uses must be recorded against the component in the technical file and checked for validity on the date the product is placed on the market.

## 3. Basis of the assessment

This assessment follows the EN IEC 63000 supplier-information approach:

1. The bill of materials (BOM) of the device was taken from *Muru Product Compliance.xlsx*, sheet `2FAK 1`.
2. For each component, the RoHS status was taken from the distributor (DigiKey) listing for the part number linked in the BOM.
3. Where available, a manufacturer RoHS certificate of compliance, declaration or material declaration was linked as evidence.
4. No analytical (XRF / laboratory) testing has been performed on the assembled product.
5. Risk assessment: components from large manufacturers with published certificates are low risk. Components with no published document are medium risk: no-name or second-source semiconductors, display modules, and hobby breakout boards or modules. For medium-risk components, a signed supplier declaration or a third-party test report (IEC 62321 series) must be obtained before signing.

## 4. Bill of materials and compliance evidence

BOM lines: **14** · Components with a fixed quantity: **21** · Lines without a published RoHS document: **1**

| # | Ref. | Qty | Description | Manufacturer | Part number (as linked) | RoHS status | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | U1 | 1 | STM32L432KCU6 | STMicroelectronics | STM32L432KCU6 | ROHS3 Compliant | [ST material declaration (IPC-1752)](https://www.st.com/resource/en/material_declaration/61mg_435xxx3_signed.pdf) |
| 2 | U2 | 1 | AP2112K-3.3 | Diodes Incorporated | AP2112K-3.3TRG1 | ROHS3 Compliant | [Diodes Inc. RoHS3/REACH statement](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6731/Diode%20RoHS3%20REACH%20247%20Jan%202025%20Statement.pdf) |
| 3 | U3 | 1 | ATECC608B | Microchip Technology | ATECC608B-SSHDA-B | ROHS3 Compliant | [Microchip RoHS CoC](https://ww1.microchip.com/downloads/aemDocuments/documents/corporate-responsibilty/environmental/product-regulatory-information/Semiconductor_EnvCoC.pdf) |
| 4 | U4 | 1 | USBLC6-2SC6 | Shenzhen Slkormicro | USBLC6-2SC6 | ROHS3 Compliant | **Missing** – request from Slkormicro |
| 5 | SW1 | 1 | Tactile SMD | C&K (Littelfuse) | PTS526 SK15 SMTR2 LFS | ROHS3 Compliant | [Littelfuse RoHS CoC](https://www.littelfuse.com/assetdocs/coc-rohs10-08-18-2022?assetguid=6d7cc3c6-97e3-4940-98fc-322868282297) |
| 6 | D1 | 1 | Green LED | Kingbright | APTD2012LZGCK | ROHS3 Compliant | [Kingbright RoHS CoC](https://www.kingbrightusa.com/webimages/certificate/Kingbright%20RoHS%20CoC.PDF) |
| 7 | R1, R2 | 2 | 10 kΩ 1% | Stackpole Electronics | RMCF0805FT10K0 | ROHS3 Compliant | [Stackpole RoHS status list](https://www.seielect.com/catalog/SEI-RoHS_Compliance_Status.pdf) |
| 8 | R3 | 1 | 330 Ω 1% | YAGEO | RC0805FR-07330RL | ROHS3 Compliant | [YAGEO RoHS compliance statement](https://yageogroup.com/content/Resource%20Library/Product%20Environmental%20Compliance/RoHS_Compliance_YAGEO.pdf) |
| 9 | R4, R5 | 2 | 4.7 kΩ 1% | YAGEO | RC0805FR-074K7L | ROHS3 Compliant | [YAGEO RoHS compliance statement](https://yageogroup.com/content/Resource%20Library/Product%20Environmental%20Compliance/RoHS_Compliance_YAGEO.pdf) |
| 10 | R6, R7 | 1 | 5.1 kΩ 1% | YAGEO | RC0805FR-075K1L | ROHS3 Compliant | [YAGEO RoHS compliance statement](https://yageogroup.com/content/Resource%20Library/Product%20Environmental%20Compliance/RoHS_Compliance_YAGEO.pdf) |
| 11 | FB1 | 1 | 600 Ω @100 MHz | Murata | BLM21PG600SN1D | ROHS3 Compliant | [Murata EMIFIL RoHS certificate](https://www.murata.com/-/media/webrenewal/products/emc/emifil/certificate/r-eu-rohs-certificate-emi-emifil.ashx?la=en) |
| 12 | C1 | 1 | 4.7 µF 10V+ X5R | Samsung Electro-Mechanics | CL10A475KA8NQNC | ROHS3 Compliant | [Samsung MLCC RoHS compliance](https://www.samsungsem.com/files/fileDown.do?key=ed1dfdfa-645e-4252-b707-17f9b1502dd1) |
| 13 | C2, C7 | 2 | 1 µF X7R | Samsung Electro-Mechanics | C0805C105K4RACTU | ROHS3 Compliant | [Samsung MLCC RoHS compliance](https://www.samsungsem.com/files/fileDown.do?key=ed1dfdfa-645e-4252-b707-17f9b1502dd1) |
| 14 | C3,C4,C5,C6,C8 | 5 | 0.1 uF X7R | Samsung Electro-Mechanics | CL10B104JB8NNNC | ROHS3 Compliant | [Samsung MLCC RoHS compliance](https://www.samsungsem.com/files/fileDown.do?key=ed1dfdfa-645e-4252-b707-17f9b1502dd1) |
| 15 | PCB | 1 | PCB | JLCPCB | Bare PCB | [x] | [x] |


## 5. Assessment summary

All 14 BOM lines are listed as RoHS compliant (ROHS3) by the distributor. A manufacturer RoHS document is linked for 13 of the 14 lines. The remaining line (U4, USBLC6-2SC6 from Shenzhen Slkormicro) has a distributor RoHS3 status only. 

## 8. Manufacturing and Assembly

| # | Item | Details | Supplier / product | RoHS evidence | Status |
|---|---|---|---|---|---|
| 1 | Bare PCB | Part no. / rev: `[ ]` · Surface finish: `[ENIG / lead-free HASL]` | `[PCB fab]` | See BOM table, PCB line | `[Open / Closed]` |
| 2 | Assembly | `[In-house / EMS name]` · Lead-free process only, no leaded solder used | `[ ]` | Assembly statement (this table, signed in section 2) | `[Open / Closed]` |
| 3 | Solder paste (reflow) | Lead-free alloy: `[e.g. SAC305]` | `[Manufacturer, product name]` | `[link / file to RoHS CoC]` | `[Open / Closed]` |
| 4 | Solder wire (hand soldering / rework) | Lead-free alloy: `[e.g. SAC305 / Sn99.3Cu0.7]` | `[Manufacturer, product name]` | `[link / file to RoHS CoC]` | `[Open / Closed]` |
| 5 | Flux | `[No-clean / rosin / water-soluble]` | `[Manufacturer, product name]` | `[link / file to RoHS CoC or SDS]` | `[Open / Closed]` |
| 6 | Cleaning agent | `[IPA / none]` | `[ ]` | `[N/A – evaporates, not in product]` | `[Open / Closed / N/A]` |
| 7 | Casing | 3D-printed, food-grade PETG · Colour: `[ ]` | Elegoo PETG `[product name]` | `[link / file to Elegoo RoHS declaration]` | `[Open / Closed]` |
| 8 | Fasteners | None – device is shipped without screws | – | N/A | N/A |
| 9 | Coating / adhesive / thermal pads | `[None / product name]` | `[ ]` | `[link / file or N/A]` | `[Open / Closed / N/A]` |
| 10 | Labels / marking | `[None / label material, printing method]` | `[ ]` | `[link / file or N/A]` | `[Open / Closed / N/A]` |
| 11 | Battery (if supplied) | `[Chemistry, capacity, part no. / N/A]` | `[ ]` | Battery Regulation (EU) 2023/1542 – outside RoHS scope | `[Open / Closed / N/A]` |
| 12 | Cables / accessories shipped | `[None / USB cable etc.]` | `[ ]` | `[link / file or N/A]` | `[Open / Closed / N/A]` |

**Assembly statement:** all assembly and rework of this product is done with lead-free solder and lead-free process materials only. No leaded solder is used, and no part is substituted without updating the BOM table and this document.

## 9. Related regulatory obligations (outside RoHS)

RoHS is one part of CE marking. The following also apply, or should be checked, for this product:

| Requirement | Applicability |
|---|---|
| EMC Directive 2014/30/EU | Applies. EMC testing is needed (the "EMC Test link" column in the BOM is currently empty). |
| Low Voltage Directive 2014/35/EU | Not applicable if the device is supplied only by USB (5 V) or a battery below 50 V AC / 75 V DC. Safety is covered via the General Product Safety Regulation (EU) 2023/988, or via RED art. 3.1a for radio devices. |
| REACH (EC) 1907/2006, Art. 33 | Confirm that no SVHC above 0.1 % w/w is present in the article. Get the REACH statements from suppliers (several are available alongside the RoHS documents above). |
| WEEE 2012/19/EU | Crossed-out wheelie-bin symbol on the product or packaging, producer registration in each EU country of sale, and take-back information. |

## 10. Technical documentation and record keeping

Detailed per object documentation can be found at LINK

## 11. Revision history

| Rev. | Date | Description | Author |
|---|---|---|---|
| 0.1 | 2026-10-03 | Initial draft generated from the BOM in *Muru Product Compliance.xlsx* | `[name]` |
