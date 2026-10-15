# รายงาน Global Master Phase 1 completion และ Phase 2 — 15 ตุลาคม 2026

## ขอบเขตและผลฐานข้อมูล

เพิ่มข้อมูลใน staging ที่ไม่ถูกอ่านโดย scanner เท่านั้น ไม่แก้ production master, allowlist, provider mappings, Scheduler, quota, raw odds/FT/fixture/snapshot history หรือ Dashboard assets ไม่มีการเปิดลีกใหม่หรือเรียก bookmaker API

Phase 1 PR #360 merge แล้ว: `0ee1e704fedcbd04e5b6ad5d98f54aa577f82b93` หลัง CI ทั้ง 4 workflows ผ่าน (full pytest 679 และ baseline unittest 27) ส่วน CI isolation แยก PR #373 merge `f9baa6940252e184e073c0fe0a1dc26b19e1441b` พร้อม guard 14 กรณี

- [PR #360](https://github.com/meepo1150-code/football-odds-scanner/pull/360)
- [PR #373](https://github.com/meepo1150-code/football-odds-scanner/pull/373)
- [Phase 1 full CI](https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38685491225)
- [Phase 1 Master QA](https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38685491241)
- [CI isolation full CI](https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38685021754)

## ลีกใหม่ 20 ลีก

| ID | ลีก | ฤดูกาล | สโมสร/สมาชิก | หลักฐานหลัก |
|---|---|---|---:|---|
| JPN-0003 | J3 League | 2026-27 | 20 | [Official](https://www.jleague.jp/en/j3/club/) |
| KOR-0003 | K3 League | 2026 | 14 | [Official](https://www.kfa.or.kr/competition/k3_2026.php) |
| CHN-0001 | Chinese Super League | 2026 | 16 | [Official](https://api.cfl-china.cn/frontweb/api/teams/latest?competition_code=CSL) |
| CHN-0002 | China League One | 2026 | 16 | [Official](https://api.cfl-china.cn/frontweb/api/teams/latest?competition_code=CL1) |
| IDN-0001 | BRI Super League | 2026-27 | 18 | [Official](https://www.ligaindonesiabaru.com/home) |
| MYS-0001 | Liga Super Malaysia | 2026-27 | 12 | [Official](https://www.malaysianfootballleague.com/Content/Post/Watch/6000) |
| VNM-0001 | LPBank V.League 1 | 2026-27 | 14 | [Official](https://vpf.vn/tin-tuc/tin-vleague/thong-cao-bao-chi-le-boc-tham-xep-lich-thi-dau-cac-giai-bong-da-chuyen-nghiep-quoc-gia-2026-27/) |
| SAU-0002 | Saudi First Division League | 2026-27 | 18 | [Official](https://www.saff.com.sa/en/teams.php?id=2&season=26) |
| ARE-0001 | ADNOC Pro League | 2026-27 | 14 | [Official](https://uaeproleague.ae/en/news-and-gallery/14-coaches-set-to-shape-the-202627-adnoc-pro-league-season) |
| QAT-0001 | Qatar Stars League | 2026-27 | 12 | [Official](https://www.qsl.qa/en/20262027) |
| USA-0002 | USL Championship | 2026 | 25 | [Official](https://www.rhodeislandfc.com/news/usl-championship-announces-season-structure-for-2026-season/) |
| CAN-0001 | Canadian Premier League | 2026 | 8 | [Official](https://www.cplsoccer.com/) |
| ARG-0002 | Primera Nacional | 2026 | 36 | [Official](https://www.afa.com.ar/11256/posts/primera-nacional-fixture-para-la-temporada-2026) |
| CHL-0001 | Liga de Primera Mercado Libre | 2026 | 16 | [Official](https://www.campeonatochileno.cl/table/liga-de-primera-grupo-1/) |
| COL-0001 | Liga BetPlay DIMAYOR | 2026 | 20 | [Official](https://www.dimayor.com.co/liga-betplay-dimayor/) |
| URY-0001 | Liga AUF Uruguaya | 2026 | 16 | [Official](https://www.auf.org.uy/liga-auf-uruguaya/) |
| ECU-0001 | LigaPro Serie A | 2026 | 16 | [Official](https://ligapro.ec/tabla-de-posiciones/) |
| PRY-0001 | Copa de Primera | 2026 | 12 | [Official](https://www.apf.org.py/clubes-apertura) |
| PER-0001 | Liga1 Te Apuesto | 2026 | 18 | [Official](https://liga1.pe/clubes/) |
| BOL-0001 | División Profesional | 2026 | 16 | [Official](https://fbf.com.bo/torneos/division-profesional/) |

สโมสรใหม่จริง 337 รายการ รวมทีมสำรอง Jeonbuk N ที่มี parent ID แยกชัดเจน ไม่ทับชุดใหญ่ จำนวนสมาชิก 337 และ source roster missing/duplicate = 0 ทั้ง 20 ลีก

Thai League 1/2 มี THA-0001/THA-0002 อยู่แล้วและยัง REVIEW ด้าน current membership จึงไม่สร้างซ้ำ ใช้ Peru และ Bolivia เป็น replacement รายละเอียดใน candidate_scope.json ไม่อนุมานรายชื่อไทยเพื่อให้ครบจำนวน

## จำนวนรวมและขอบเขตการนับ

| ฐาน | Countries/namespaces | Competitions | Canonical club rows | Memberships |
|---|---:|---:|---:|---:|
| Production เดิม | 61 | 105 | 1,374 | 1,203 |
| รวม Production + Phase 1 + Phase 2 staging | 82 | 136 | 1,928 | 1,757 |

ตัวเลขรวมไม่ใช่จำนวนลีก/สโมสรที่เปิดสแกน Production ข้อมูลเดิมยังมี reserved duplicate redirect 1 แถว จึงไม่ควรเรียกจำนวน canonical rows ทั้งหมดว่า active unique clubs ที่พร้อมเดิมพัน

## Provider readiness และรายการ REVIEW

Production mappings เดิม 1,295 = 92 competitions + 1,203 clubs คงเดิม Phase 2 พบ catalog candidates ครบ 20 competitions; exact normalized source-label candidates 144/337 clubs (42.7%) อีก 193 สโมสร UNRESOLVED ทั้งหมด 337 ยังไม่มี verified provider binding (0/337) และ competition candidates ยังไม่มี verified season/stage binding (0/20) ไม่ใช้ผลตรงชื่อเป็นข้อพิสูจน์ตัวตน

Phase 1 candidates 11 competitions ยังคง REVIEW เช่นกัน ไม่มี mapping ใหม่เปิดใช้ใน Production จึงไม่อ้างว่า PROVIDER_MAPPING_VERIFIED หรือ READY_FOR_FUTURE_ACTIVATION เป็นจริง

- Cached OddsPapi snapshot วันที่ 11 ต.ค. 2026; hash และ exact fixture references เก็บใน evidence files ไม่ยืนยัน live availability วันที่ 15
- Chile, Colombia, Paraguay, Bolivia มี catalog IDs หลาย stage/legacy ต้องตรวจ season/stage แยก ไม่เลือก ID จากชื่อที่ใกล้กัน
- PropLine: UNRESOLVED ไม่มี cached evidence ที่ยืนยันตัวตนลีก/ทีมชุดนี้ ห้ามเดา ID
- Jeonbuk: KFA label ทั่วไปต้องจำกัด K3 scope; owner publication ยืนยัน N/reserve squad โดยรักษา first-team parent ID เดิม
- DPMM: BRN namespace และ MYS membership ตาม official club + MFL sources
- รายชื่อเป็น official published roster label ไม่รับรองชื่อนิติบุคคลทุกทีม ไม่อนุมาน successor/merger จากชื่อใหม่
- Current membership และ material changes ตรวจแล้ว แต่ legal promotion/relegation/corporate history ยัง partial; format notes เป็นรายละเอียดประกอบ ไม่ใช่การรับรองกฎทุก stage เพื่อใช้ runtime
- Colombia จำกัด Liga II; Peru จำกัด Clausura; ไม่ขยายการรับรองย้อนหลังเกินหลักฐาน

## Validation และ Production isolation

Baseline main `0ee1e704fedcbd04e5b6ad5d98f54aa577f82b93` มี hash ของไฟล์ production 361 ไฟล์ รวม scanner code, workflows, config, controls, master และ normalized history Continuous validator ตรวจ master/catalog โดยไม่ freeze operational report ที่ scheduled scans อัปเดตได้ตามปกติ Full manifest คงไว้ตรวจย้อนหลัง

Automated checks ครอบคลุม uniqueness, missing teams, foreign keys, frozen ID ledger, cross-border/reserve identity, provider namespace/fixture proof, official evidence domain/season, stage extension, exclusions, deterministic build, production loader isolation รวม regression suite เดิมด้าน Dashboard และ workflow guard

ผล local และ CI ของ head สุดท้ายให้ดู qa.json และ PR checks ส่วนผล merge และ SHA สุดท้ายอยู่ใน PR ไม่บันทึกค่าที่คาดการณ์ไว้ก่อนเกิดจริง

## Dashboard และรอบสแกนที่สังเกตจริง

หน้าเว็บตอบ HTTP 200 ตรวจเมื่อ 2026-10-15T05:20:25.595682+00:00 deployment source `b3120fca47d97ee44251548aef967d6f6d5ee228` run [38685364326](https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38685364326)

รอบล่าสุดที่เห็น: target 2026-10-15T00:00:00+07:00; actual 2026-10-15T00:03:58.899862+07:00; valid snapshots 11; API errors 0; Scan Health **WARNING** เป็นสถานะ operational เดิม ไม่กล่าวว่า PASS หรือทุกคู่เก็บครบ

[รอบสแกนจริง](https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38603378281) — ไม่มีการ dispatch scanner/recovery/deploy สำหรับการเพิ่มฐานข้อมูลนี้ รอบในอนาคตยังไม่ถึงเวลาจึงรับรองผลล่วงหน้าไม่ได้

## ก่อน activation

ต้องทำ PR แยก: ตรวจ exact provider competition season/stage และ participant bindings, แก้ alias ambiguities, ตัดสิน legal identity ที่มี rename/relocation, ตรวจ live market coverage/quote freshness ภายใต้ quota ledger และทดสอบ cohort/settlement/FT join ก่อนขยาย allowlist การ merge staging ไม่มอบสิทธิ์เปิดสแกนอัตโนมัติ

ประโยชน์ของ staging คือเก็บฐานที่ตรวจสอบและทำซ้ำได้โดยไม่ใช้ quota หรือเปลี่ยน scan universe ข้อจำกัดคือยังสแกนลีกใหม่ไม่ได้ ความเสี่ยงสำคัญก่อน activation คือ mapping ผิด stage หรือผูกทีมสำรองกับชุดใหญ่ จึงคง admission เป็น REVIEW และ activation_allowed=false ทุกแถว
