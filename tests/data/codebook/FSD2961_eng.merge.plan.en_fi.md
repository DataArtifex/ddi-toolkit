# DDI-Codebook Multilingual Merge Report: `plan-f2aa9509`

**Generated:** 2026-10-15T18:19:38.460597+00:00  
**Status:** `APPROVED`  
**Review Gate Approved:** `No`  

## 1. Input Codebooks
| Document | File Path | Language | Study ID | Variables | Files |
|---|---|---|---|---|---|
| **Canonical** | `/Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/codebook/FSD2961_eng.xml` | `en` | `—` | 0 | 0 |
| **Translated** | `/Users/pascal/Library/CloudStorage/Dropbox/git-dartfx/ddi-toolkit/tests/data/codebook/FSD2961_fin.xml` | `fi` | `—` | 34 | 1 |

## 2. Assessment Metrics
| Metric | Count | Note |
|---|---|---|
| Total Elements Compared | 1 | |
| Exact Matches | 1 | Compatible elements across files |
| Missing Translations | 0 | Canonical items lacking translated text |
| Summary Statistics Divergences | 0 | `sumStat` discrepancies |
| Category Frequency Divergences | 0 | `catStat` discrepancies |
| Missing Attribute Divergences | 0 | `@missing` discrepancies |
| Unmatched Canonical Items | 0 | Items only in canonical |
| Unmatched Translated Items | 34 | Orphan variables in translated |
| **Pending Human Review Items** | **0** | Requires approval to proceed |

## 3. Side-by-Side Study & Document Metadata
| Element | Canonical (`en`) | Translated (`fi`) | Merge Outcome |
|---|---|---|---|
| **Study Title** | Finnish Perspectives on Light Pollution 2011-2012 | Suomalaisten näkemyksiä valosaasteesta 2011-2012 | Added parallel title (`parTitl [xml:lang='fi']`) |
| **Document Title** | DDI description: Finnish Perspectives on Light Pollution 2011-2012 | DDI-kuvailu: Suomalaisten näkemyksiä valosaasteesta 2011-2012 | Added doc parallel title (`parTitl [xml:lang='fi']`) |
| **Study Abstract** | The survey charted opinions on light pollution and the use of artificial lighting. The respondents were asked to indicate to what extent they agreed with severa... | Kyselyssä tarkasteltiin suhtautumista valosaasteeseen ja keinovalon käyttöön. Aluksi vastaajilta tiedusteltiin mielipiteitä keinovalaistuksesta erilaisin väittä... | Merged both language abstracts |
| **Keywords** | electric lighting (ELSST), human environment (ELSST), lighting (ELSST), light pollution | valosaaste (YSO), ympäristöhaitat (YSO), valaistus (YSO), keinovalo (YSO), valo (YSO) (+2 more) | Merged all keywords (4 `en` + 7 `fi`) |
| **Topic Classifications** | Social sciences (OKM), Natural sciences (OKM), Environment and conservation (CESSDA Topic Classification) | Yhteiskuntatieteet (OKM), Luonnontieteet (OKM), Ympäristönsuojelu ja ympäristöongelmat (CESSDA Topic Classification) | Merged all topics (3 `en` + 3 `fi`) |
| **Geographic Coverage** | Finland | Suomi | Merged localized geographic terms |
| **Universe** | Finnish people | Suomalaiset | Merged universe statements |

## 5. Side-by-Side Variables & Questions Comparison
| Variable | Label (`en`) | Label (`fi`) | Questions | Categories | Merge Status |
|---|---|---|---|---|---|
| `FSD_NO` | — | [fsd_no] Aineistonumero (lisätty FSD:ssä) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `FSD_VR` | — | [fsd_vr] Aineistoversio (lisätty FSD:ssä) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `FSD_ID` | — | [fsd_id] Havaintotunnus (lisätty FSD:ssä) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `BV1` | — | [bv1] Vastausaika | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q1_1` | — | [q1_1] Mitä mieltä olet alla olevista väittämistä: Keinovalaistuksen aiheuttama valosaaste on levinnyt liian laajalle | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_2` | — | [q1_2] Mitä mieltä olet alla olevista väittämistä: Jokaisen pitäisi pystyä näkemään kirkas tähtitaivas ja Linnunrata asuinpaikaltaan | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_3` | — | [q1_3] Mitä mieltä olet alla olevista väittämistä: Tievalaistus on välttämätöntä autoilijoille | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_4` | — | [q1_4] Mitä mieltä olet alla olevista väittämistä: Yöllinen valaistus lisää turvallisuutta asuinalueilla | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_5` | — | [q1_5] Mitä mieltä olet alla olevista väittämistä: Valosaaste aiheuttaa merkittäviä haittoja luonnolle | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_6` | — | [q1_6] Mitä mieltä olet alla olevista väittämistä: Valosaaste aiheuttaa merkittäviä terveyshaittoja ihmisille | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_7` | — | [q1_7] Mitä mieltä olet alla olevista väittämistä: Luonnonsuojelualueilla ei saa olla yhtään keinovaloa | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_8` | — | [q1_8] Mitä mieltä olet alla olevista väittämistä: Hämärät puistot ovat pelottavia öisin | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_9` | — | [q1_9] Mitä mieltä olet alla olevista väittämistä: Koristevalot pihoissa ja parvekkeilla ovat häiritseviä | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_10` | — | [q1_10] Mitä mieltä olet alla olevista väittämistä: Asuinalueeni viihtyvyys kärsii liiallisesta keinovalosta | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_11` | — | [q1_11] Mitä mieltä olet alla olevista väittämistä: Matkapuhelinverkon tukiasemien valot pilaavat maisemaa | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_12` | — | [q1_12] Mitä mieltä olet alla olevista väittämistä: Ulkotilojen mainosvalot ovat häiritseviä | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_13` | — | [q1_13] Mitä mieltä olet alla olevista väittämistä: Viranomaiset suhtautuvat valosaasteeseen vähätellen | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_14` | — | [q1_14] Mitä mieltä olet alla olevista väittämistä: Vältän itse aina turhaa valon käyttöä | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_15` | — | [q1_15] Mitä mieltä olet alla olevista väittämistä: Mielialani laskee voimakkaasti pimeänä vuodenaikana | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_16` | — | [q1_16] Mitä mieltä olet alla olevista väittämistä: Mahdollisuus luonnollisen pimeyden kokemiseen on minulle tärkeä | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_17` | — | [q1_17] Mitä mieltä olet alla olevista väittämistä: Valistus ja tiedotus ovat tehokkaita keinoja valosaasteen vähentämiseen | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_18` | — | [q1_18] Mitä mieltä olet alla olevista väittämistä: Lainsäädännön tiukentaminen on tehokas keino valosaasteen vähentämiseen | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_19` | — | [q1_19] Mitä mieltä olet alla olevista väittämistä: Valaistustekniikan kehittäminen on tehokas keino valosaasteen vähentämiseen | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q1_20` | — | [q1_20] Mitä mieltä olet alla olevista väittämistä: Sähkön hinnan korottaminen on tehokas keino valosaasteen vähentämiseen | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q2` | — | [q2] Missä ja milloin olet kokenut valosaasteen erityisen häiritseväksi? Mistä keinovalo on ollut peräisin? (Avokysymys) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q3` | — | [q3] Millaisissa paikoissa olet kokenut pimeyden tai luontaisen hämäryyden miellyttäväksi? (Avokysymys) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q4` | — | [q4] Oletko itse yrittänyt vähentää valosaasteen syntymistä tai häiritsevälle valolle altistumista? Miten? (Avokysymys) | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q5` | — | [q5] Syntymävuosi | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q6` | — | [q6] Sukupuoli | Translated only (`fi`) | 2 categories | Unmatched (translated only) |
| `Q7` | — | [q7] Asuinkunta | Translated only (`fi`) | Continuous / Numeric | Unmatched (translated only) |
| `Q8` | — | [q8] Asuinalue | Translated only (`fi`) | 4 categories | Unmatched (translated only) |
| `Q9` | — | [q9] Koulutus | Translated only (`fi`) | 7 categories | Unmatched (translated only) |
| `Q10` | — | [q10] Harrastatko aktiivisesti tähtitiedettä? | Translated only (`fi`) | 2 categories | Unmatched (translated only) |
| `Q11` | — | [q11] Oletko luonto- tai ympäristöjärjestön jäsen? | Translated only (`fi`) | 2 categories | Unmatched (translated only) |

## 6. Discrepancies & Resolutions Manifest
| ID | Target Element | Issue Code | Canonical Value | Translated Value | Action | Approval |
|---|---|---|---|---|---|---|
| `disc-001` | `dataDscr/var[@name='FSD_NO']` | `UNMATCHED_TRANSLATION` | — | FSD_NO | `drop` | Auto-Resolved |
| `disc-002` | `dataDscr/var[@name='FSD_VR']` | `UNMATCHED_TRANSLATION` | — | FSD_VR | `drop` | Auto-Resolved |
| `disc-003` | `dataDscr/var[@name='FSD_ID']` | `UNMATCHED_TRANSLATION` | — | FSD_ID | `drop` | Auto-Resolved |
| `disc-004` | `dataDscr/var[@name='BV1']` | `UNMATCHED_TRANSLATION` | — | BV1 | `drop` | Auto-Resolved |
| `disc-005` | `dataDscr/var[@name='Q1_1']` | `UNMATCHED_TRANSLATION` | — | Q1_1 | `drop` | Auto-Resolved |
| `disc-006` | `dataDscr/var[@name='Q1_2']` | `UNMATCHED_TRANSLATION` | — | Q1_2 | `drop` | Auto-Resolved |
| `disc-007` | `dataDscr/var[@name='Q1_3']` | `UNMATCHED_TRANSLATION` | — | Q1_3 | `drop` | Auto-Resolved |
| `disc-008` | `dataDscr/var[@name='Q1_4']` | `UNMATCHED_TRANSLATION` | — | Q1_4 | `drop` | Auto-Resolved |
| `disc-009` | `dataDscr/var[@name='Q1_5']` | `UNMATCHED_TRANSLATION` | — | Q1_5 | `drop` | Auto-Resolved |
| `disc-010` | `dataDscr/var[@name='Q1_6']` | `UNMATCHED_TRANSLATION` | — | Q1_6 | `drop` | Auto-Resolved |
| `disc-011` | `dataDscr/var[@name='Q1_7']` | `UNMATCHED_TRANSLATION` | — | Q1_7 | `drop` | Auto-Resolved |
| `disc-012` | `dataDscr/var[@name='Q1_8']` | `UNMATCHED_TRANSLATION` | — | Q1_8 | `drop` | Auto-Resolved |
| `disc-013` | `dataDscr/var[@name='Q1_9']` | `UNMATCHED_TRANSLATION` | — | Q1_9 | `drop` | Auto-Resolved |
| `disc-014` | `dataDscr/var[@name='Q1_10']` | `UNMATCHED_TRANSLATION` | — | Q1_10 | `drop` | Auto-Resolved |
| `disc-015` | `dataDscr/var[@name='Q1_11']` | `UNMATCHED_TRANSLATION` | — | Q1_11 | `drop` | Auto-Resolved |
| `disc-016` | `dataDscr/var[@name='Q1_12']` | `UNMATCHED_TRANSLATION` | — | Q1_12 | `drop` | Auto-Resolved |
| `disc-017` | `dataDscr/var[@name='Q1_13']` | `UNMATCHED_TRANSLATION` | — | Q1_13 | `drop` | Auto-Resolved |
| `disc-018` | `dataDscr/var[@name='Q1_14']` | `UNMATCHED_TRANSLATION` | — | Q1_14 | `drop` | Auto-Resolved |
| `disc-019` | `dataDscr/var[@name='Q1_15']` | `UNMATCHED_TRANSLATION` | — | Q1_15 | `drop` | Auto-Resolved |
| `disc-020` | `dataDscr/var[@name='Q1_16']` | `UNMATCHED_TRANSLATION` | — | Q1_16 | `drop` | Auto-Resolved |
| `disc-021` | `dataDscr/var[@name='Q1_17']` | `UNMATCHED_TRANSLATION` | — | Q1_17 | `drop` | Auto-Resolved |
| `disc-022` | `dataDscr/var[@name='Q1_18']` | `UNMATCHED_TRANSLATION` | — | Q1_18 | `drop` | Auto-Resolved |
| `disc-023` | `dataDscr/var[@name='Q1_19']` | `UNMATCHED_TRANSLATION` | — | Q1_19 | `drop` | Auto-Resolved |
| `disc-024` | `dataDscr/var[@name='Q1_20']` | `UNMATCHED_TRANSLATION` | — | Q1_20 | `drop` | Auto-Resolved |
| `disc-025` | `dataDscr/var[@name='Q2']` | `UNMATCHED_TRANSLATION` | — | Q2 | `drop` | Auto-Resolved |
| `disc-026` | `dataDscr/var[@name='Q3']` | `UNMATCHED_TRANSLATION` | — | Q3 | `drop` | Auto-Resolved |
| `disc-027` | `dataDscr/var[@name='Q4']` | `UNMATCHED_TRANSLATION` | — | Q4 | `drop` | Auto-Resolved |
| `disc-028` | `dataDscr/var[@name='Q5']` | `UNMATCHED_TRANSLATION` | — | Q5 | `drop` | Auto-Resolved |
| `disc-029` | `dataDscr/var[@name='Q6']` | `UNMATCHED_TRANSLATION` | — | Q6 | `drop` | Auto-Resolved |
| `disc-030` | `dataDscr/var[@name='Q7']` | `UNMATCHED_TRANSLATION` | — | Q7 | `drop` | Auto-Resolved |
| `disc-031` | `dataDscr/var[@name='Q8']` | `UNMATCHED_TRANSLATION` | — | Q8 | `drop` | Auto-Resolved |
| `disc-032` | `dataDscr/var[@name='Q9']` | `UNMATCHED_TRANSLATION` | — | Q9 | `drop` | Auto-Resolved |
| `disc-033` | `dataDscr/var[@name='Q10']` | `UNMATCHED_TRANSLATION` | — | Q10 | `drop` | Auto-Resolved |
| `disc-034` | `dataDscr/var[@name='Q11']` | `UNMATCHED_TRANSLATION` | — | Q11 | `drop` | Auto-Resolved |

---
*Report generated by Data Artifex DDI Toolkit (`dartfx-ddi`).*