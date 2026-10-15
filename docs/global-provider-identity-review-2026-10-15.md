# Cached identity review และสมาชิกไทยลีก — 15 ตุลาคม 2026

## ผลลัพธ์และขอบเขต

- ปิด blocker รายชื่อสมาชิกปัจจุบันของ THA-0001 (16 ทีม) และ THA-0002 (18 ทีม) ฤดูกาล 2026/27
- ใช้ Competition ID เดิมทั้งสองรายการ ไม่เพิ่มลีกซ้ำ ไม่เพิ่มในเป้าหมาย 20 ลีกใหม่ของ Phase 2
- เพิ่ม canonical club identities 34 รายการและ season memberships 34 รายการใน staging เท่านั้น
- ยืนยัน cached competition identity 22/33 รายการ และ cached participant identity 253/588 รายการ
- คง REVIEW 11 competitions และ UNRESOLVED 335 clubs; ไม่เติม Provider ID ด้วยการเดา
- Provider requests ของงานนี้ = 0; ใช้ snapshot ที่เก็บเมื่อ 2026-10-11T14:32:50.571229+00:00
- ไม่รับรอง provider season/stage ID, full-roster coverage, bookmaker market availability หรือ live odds coverage
- activation_allowed=false ทุกระเบียน ไม่มีการเปิดลีกหรือแก้ production mapping

ผล Phase 1 (11 ลีก/217 สโมสร) และ Phase 2 (20 ลีกใหม่/337 สโมสร) ยังอยู่แยก staging ตามเดิม
ส่วนเสริมไทยลีกนี้เพิ่มอีก 34 สโมสรใน competitions ที่มีอยู่แล้ว
รวม production + staging: 82 country namespaces, 136 competitions, 1,962 canonical rows,
1,961 distinct canonical_club_id และ 1,791 memberships โดย duplicate redirect เก่าหนึ่งรายการไม่ถูกแก้ในงานนี้
Production master เองยังเป็น 61 countries, 105 competitions, 1,374 club rows และ 1,203 memberships
ตัวเลขทั้งหมดนี้ไม่ใช่จำนวนลีกที่เปิดสแกนจริง

## หลักฐานไทยลีก

หน้าเริ่มต้น: https://thaileague.co.th/v1/tables/
public API เป็น endpoint ที่หน้าเว็บทางการเรียก ไม่ใช่ OddsPapi หรือ API ราคา

1. season-dropdown-public ระบุ season 33 = 2026/2027 และ season 32 = 2025/2026
2. tournament-dropdown-public?season=33 ระบุ tournament 224 และ 226 พร้อมชื่อฤดูกาล
3. tournament-team-dropdown-public ระบุทีม 16 และ 18 ทีม รวมชื่อไทยและอังกฤษใน record เดียวกัน
4. stage-standing-public/dashboard ระบุชื่อและ tournament-team ID ตรงกับรายชื่อครบทั้งสองลีก
5. tournament-team-dropdown-public ของ 207 และ 208 ใช้เปรียบเทียบสมาชิกฤดูกาล 2025/26

เก็บ factual identity extracts, URL, UTC retrieval timestamp และ SHA256 ของ raw response ใน
data/research/thailand_membership_completion/evidence.json
ไม่ใช้รายชื่อผู้ผ่านเข้ารอบบอลถ้วยมารับรองรายชื่อครบลีก
ชื่อไทย–อังกฤษมาจาก record ทางการเดียวกัน ไม่ใช่ transliteration ที่เดาขึ้น
official club IDs และ tournament-team IDs แยก namespace จาก canonical ID และ OddsPapi ID โดยเด็ดขาด

membership_changes ใน qa.json รับรองเพียงการเข้าหรือออกจากรายชื่อระหว่างสองฤดูกาล
กลไกการเลื่อนชั้น/ตกชั้น การถอนทีม licensing และ format รอบ playoff ยังคง REVIEW
ไม่อนุมานผลทางกฎหมายจากรายชื่อที่เปลี่ยน

## เกณฑ์ cached identity verification

- candidate tournament ID ต้องมี catalog record เดียว พร้อมชื่อและประเทศตรงกับหลักฐานเดิม
- fixture ต้องมี ID, ชื่อ tournament ตรง catalog, timestamp ที่ parse ได้พร้อม timezone และอยู่ในช่วง October 2026
- A-League ใช้ตั้งแต่ 16 ตุลาคม 2026 ตามขอบเขตฤดูกาลประกาศใหม่ ไม่ใช้ fixtures ก่อนเริ่ม
- ทั้งสองทีมของ fixture ต้องตรงชื่อ canonical/alias ทางการแบบไม่กำกวม ภายใน roster เดียวกัน
- participant ID/name ต้องตรง cached participant catalog; canonical clubs และ participant IDs ของสองฝั่งต้องไม่ซ้ำกัน
- อย่างน้อยสอง fixtures และสี่สโมสรที่ไม่ซ้ำ จึงรับรองตัวตน competition จาก candidate ID ที่ผ่านเพียงหนึ่งรายการ
- conflicting fixture versions, competing provider IDs, IDs ชน production หรือซ้ำระหว่าง canonical competitions ไม่ผ่าน
- ไม่ลบ reserve qualifier หรือเลขทีม; ชื่อ KFA แบบ generic ของ Jeonbuk ไม่ใช้แทน N squad
- Unicode normalization คงอักขระและวรรณยุกต์ไทย ไม่ทำให้ชื่อ non-Latin กลายเป็น empty-string match
- ไม่ใช้ fuzzy matching และไม่ยกสถานะเพียงเพราะชื่อคล้ายกัน
- fixture dates ไม่ใช่หลักฐาน season/stage binding: ค่า provider_season_stage_verified ยังคง false

| Competition | Cached competition ID | Verified clubs |
|---|---:|---:|
| ARE-0001 — ADNOC Pro League | REVIEW | 0 |
| ARG-0001 — Primera División | REVIEW | 0 |
| ARG-0002 — Primera Nacional | REVIEW | 0 |
| AUS-0001 — A-League Men | 136 | 8 |
| BOL-0001 — División Profesional | REVIEW | 0 |
| BRA-0001 — Campeonato Brasileiro Série A | 325 | 5 |
| BRA-0002 — Campeonato Brasileiro Série B | REVIEW | 0 |
| CAN-0001 — Canadian Premier League | 28432 | 6 |
| CHL-0001 — Liga de Primera Mercado Libre | 27665 | 7 |
| CHN-0001 — Chinese Super League | 649 | 16 |
| CHN-0002 — China League One | 782 | 13 |
| COL-0001 — Liga BetPlay DIMAYOR | REVIEW | 0 |
| ECU-0001 — LigaPro Serie A | 240 | 4 |
| IDN-0001 — BRI Super League | 1015 | 14 |
| JPN-0001 — J1 League | 196 | 17 |
| JPN-0002 — J2 League | 402 | 20 |
| JPN-0003 — J3 League | 2094 | 18 |
| KOR-0001 — K League 1 | REVIEW | 0 |
| KOR-0002 — K League 2 | REVIEW | 0 |
| KOR-0003 — K3 League | REVIEW | 0 |
| MEX-0001 — Liga MX | 27464 | 6 |
| MYS-0001 — Liga Super Malaysia | 1000 | 6 |
| PER-0001 — Liga1 Te Apuesto | 406 | 8 |
| PRY-0001 — Copa de Primera | REVIEW | 0 |
| QAT-0001 — Qatar Stars League | 825 | 8 |
| SAU-0001 — Saudi Pro League | 955 | 5 |
| SAU-0002 — Saudi First Division League | 2298 | 10 |
| THA-0001 — BYD SEALION 6 LEAGUE I 2026/27 | 1032 | 13 |
| THA-0002 — BYD SEAL 5 LEAGUE II 2026/27 | 19232 | 14 |
| URY-0001 — Liga AUF Uruguaya | REVIEW | 0 |
| USA-0001 — Major League Soccer | 242 | 26 |
| USA-0002 — USL Championship | 28163 | 24 |
| VNM-0001 — LPBank V.League 1 | 626 | 5 |

รายการ REVIEW ที่เหลือ: UAE, Argentina Primera และ Primera Nacional, Bolivia, Brazil Série B,
Colombia, Korea K1/K2/K3, Paraguay และ Uruguay เนื่องจากชื่อ official กับ cached names
ยังไม่มี alias ที่พิสูจน์ได้ หรือ paired roster observations ไม่ถึงเกณฑ์
ไม่ผ่อนเกณฑ์เพื่อให้ครบจำนวน และ PropLine ไม่มีหลักฐานใหม่ที่รับรองได้

## Deterministic rebuild และ tests

```sh
python data/research/thailand_membership_completion/build.py
python data/research/global_provider_identity_review/review.py
python -m pytest -q
python data/master/validate_uefa_master.py
python -m unittest discover -s data/master -p 'test_uefa_registry.py' -v
```

ไม่มี network call ใน builder, reviewer หรือ tests; --write เขียนได้เฉพาะ derived staging artifacts
hash pins ป้องกันการเปลี่ยน official evidence/identity ledger โดยไม่ review migration
regression tests ครอบคลุม deterministic build, source hash, provider namespace, invalid/out-of-window dates,
two-sided fixture proof, duplicate/conflicting fixtures, absent/duplicate catalog, missing participant catalog,
existing production mapping conflicts, multiple participant IDs, cross-border DPMM และ generic reserve ambiguity
tests ไทยลีกปฏิเสธ evidence, identity ledger หรือ generated dataset ที่ถูกแก้ไม่ตรง rebuild

## Production isolation และข้อจำกัด

Diff ของงานนี้ต้องมีเพียง data/research สอง directories, test และเอกสารนี้
ไม่แก้ scanner, scheduler, workflows, quota, production tables, raw odds, FT, fixture history หรือ dashboard
Full suite เดิมมี tests ที่สร้าง synthetic scan-health diagnostics ลง tracked paths สองไฟล์
release audit จึงคืนเฉพาะสองไฟล์ที่ tests สร้างและตรวจ production manifest หลังรันอีกครั้ง
remote scheduled jobs อาจสร้าง runtime data หรือ dashboard deployment ใหม่ได้โดยอิสระจาก PR นี้
จึงตรวจการเปลี่ยนแปลงแยกตาม parent commit และไม่กล่าวว่า scheduled data ต้องหยุดนิ่ง

Dashboard HTTP 200 ระหว่าง audit; latest observed scan คือ 2026-10-15 00:03:58.899862 Asia/Bangkok,
11 valid odds, 0 API errors และสถานะ WARNING ที่มีอยู่เดิม ไม่รายงานเป็น PASS
ไม่มีการ dispatch สแกนหรือ deploy เพื่อทดสอบงานฐานข้อมูลนี้

ก่อนเปิดใช้งานต้องมี PR แยกสำหรับ season/stage binding, complete participant coverage,
market/bookmaker availability, quota approval/budget, scan configuration, monitoring และ rollback
DATABASE roster verification ไม่เท่ากับ READY_FOR_FUTURE_ACTIVATION ของ scanner
CI URLs และ merge SHA สุดท้ายบันทึกใน PR และรายงานส่งมอบหลัง safety gates ผ่านจริง
