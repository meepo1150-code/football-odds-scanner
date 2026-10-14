# รายงานตรวจสอบ Global Master Database — Phase 1

วันที่อ้างอิงข้อมูล: **14 ตุลาคม 2026 (Asia/Bangkok)**

ขอบเขต: เพิ่มข้อมูลฐานฟุตบอลผ่าน staging เท่านั้น ไม่เปิดลีกใน Scanner ไม่ merge และไม่ deploy

## A. Baseline ที่ตรวจจริง

- Main SHA: `a4aec8ccc7689435f184126d1008be47d1626825`
- Main tree: `64f467a9870a7efa50fd3656f94ee5bdcbc8f740`
- อ่าน Project Instructions ที่แนบครบแล้ว เอกสารวันที่ 9 ก.ย. มีสถานะเก่า จึงใช้ repository เป็นหลัก ไม่กลับไปแก้ PR #74
- ไม่มี `AGENTS.md` ใน checkout ที่ตรวจ
- ตรวจ PR #309: merged วันที่ 11 ต.ค. 2026, merge SHA `78447610050312baad9b3cf76f5852ddce3073af`

| ตารางเดิม | จำนวนจริง | หมายเหตุ |
|---|---:|---|
| Countries | 61 | IN_SCOPE 50 / REVIEW 6 / excluded domestic 4 / cross-border 1 |
| Competitions | 105 | VERIFIED_OFFICIAL 81 / REVIEW 9 / EXCLUDED_USER 6 / REGISTERED_OFFICIAL 9 |
| Canonical clubs | 1,374 | current scoped 1,203 / outside scoped roster 170 / reserved duplicate redirect 1 |
| Current memberships | 1,203 | 50 associations / 81 divisions |
| Legacy teams | 643 | เก็บไว้ ไม่ใช่ current canonical authority |
| Provider mappings | 1,295 | competitions 92 / clubs 1,203; VERIFIED_PROVIDER_SNAPSHOT |

สถานะ `REGISTERED_OFFICIAL` ไม่ได้มีความหมายเดียวกับ `VERIFIED_OFFICIAL`; ถ้วย 11 รายการมี evidence registry แยกต่างหาก ไม่ได้อนุมานสมาชิกจากลีก

## B. ฐานข้อมูลใหม่

ตำแหน่ง: `data/research/global_master_phase1/`

| รายการ | จำนวน |
|---|---:|
| Country namespaces ที่เพิ่มใหม่ | 7 |
| Country IDs เดิมที่ reuse | 3 |
| ลีกใหม่ใน staging | 11 |
| Canonical clubs ใหม่ | 217 |
| Clubs ที่ reuse | 0 |
| Memberships | 217 |
| Clubs ที่ยัง REVIEW | 0 |
| Evidence-backed aliases | 25 |
| Production mappings ที่เพิ่ม | 0 |

Reuse `JPN`, `KOR`, `BRA` โดยคงแถวเดิม เพิ่ม namespace `AUS`, `NZL`, `USA`, `CAN`, `ARG`, `MEX`, `SAU` ใน staging เท่านั้น จากการตรวจทั้ง canonical, legacy teams และ assignment ledger เดิม ไม่พบ club ของขอบเขตนี้ให้ reuse

รหัสสโมสรใช้ COUNTRY-3 letters และรหัสลีก COUNTRY-4 digits ตาม convention เดิม ไม่มีการใช้ Provider ID เป็น Canonical ID สมาชิกลีกและประเทศสโมสรแยกกัน: 3 สโมสรแคนาดาใน MLS และ 2 สโมสรนิวซีแลนด์ใน A-League ใช้ประเทศสโมสรจริงเป็น namespace

## C. League Completion Matrix

ทุกแถวมี missing 0, duplicate 0, evidence coverage 100% ของสมาชิกที่นำเข้า สถานะ membership คือ `VERIFIED_OFFICIAL`; สถานะ competition admission ยังคง `REVIEW` และ database เป็น `STAGING_ONLY`

| ประเทศ / host | ลีก | ฤดูกาล / stage ที่ยืนยัน | Expected | Verified | Missing | Evidence | Database |
|---|---|---|---:|---:|---:|---|---|
| Japan | J1 League | 2026-27 | 20 | 20 | 0 | Official | Staging |
| Japan | J2 League | 2026-27 | 20 | 20 | 0 | Official | Staging |
| South Korea | K League 1 | 2026 | 12 | 12 | 0 | Official | Staging |
| South Korea | K League 2 | 2026 | 17 | 17 | 0 | Official | Staging |
| Australia / NZ clubs | A-League Men | 2026-27: next announced | 12 | 12 | 0 | Official | Staging |
| USA / Canada | MLS | 2026 | 30 | 30 | 0 | Official | Staging |
| Brazil | Série A | 2026 | 20 | 20 | 0 | Official indexed roster | Staging |
| Brazil | Série B | 2026 | 20 | 20 | 0 | CBF regulations annex A | Staging |
| Argentina | Primera División | 2026: Apertura / Clausura | 30 | 30 | 0 | LPF + AFA | Staging |
| Mexico | Liga MX | 2026-27: Apertura 2026 only | 18 | 18 | 0 | Official PDF + club directory | Staging |
| Saudi Arabia | Saudi Pro League | 2026-27 | 18 | 18 | 0 | Official scheduling list | Staging |

แหล่งข้อมูลหลัก:

- ญี่ปุ่น: [J1](https://www.jleague.jp/en/j1/club/), [J2](https://www.jleague.jp/en/j2/club/), [ประกาศ club allocation 2026/27](https://www.jleague.jp/news/article/32852/)
- เกาหลี: [ระเบียบการแข่งขัน 2026 ข้อ 5 ของแต่ละลีก](https://www.kleague.com/about/competition.do)
- ออสเตรเลีย: [รายชื่อครบผ่าน first five fixtures](https://aleagues.com.au/news/aleague-men-2026-27-fixtures-first-five-news/), [Western United participation termination](https://aleagues.com.au/news/australian-professional-leagues-statement-regarding-western-united/)
- MLS: [2026 competition guidelines](https://www.mlssoccer.com/news/2026-mls-competition-guidelines), [official clubs](https://www.mlssoccer.com/clubs/)
- บราซิล: [CBF Série A 2026 teams](https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026), [CBF Série B regulations, page 16](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/REC_Brasileiro_Serie_B_2026_85d55b9f72.pdf)
- อาร์เจนตินา: [LPF current senior club directory / Clausura article](https://www.ligaprofesional.ar/?p=84377), [AFA 2026 fixtures](https://www.afa.com.ar/11159/posts/agenda-para-la-temporada-2026-de-la-liga-profesional)
- เม็กซิโก: [Liga MX official Apertura calendar, page 2](https://d1ezr1jf3kzw59.cloudfront.net/docs/publicaciones/ligamx/2026-2027/1/calendario-liga-mx-torneo-apertura-2026.pdf), [joint official Leagues Cup club directory](https://www.leaguescup.com/clubs/)
- ซาอุดีอาระเบีย: [official 2026/27 scheduling list](https://www.spl.com.sa/en/news/spl-announces-2026-27-rsl-fixture-schedule)

ข้อจำกัดที่ต้องอ่านร่วมกับ PASS: บราซิล Série A เปิดหน้าตรง timeout จึงอ่านรายชื่อทั้ง 20 จากผลค้นหาที่มีต้นทาง CBF และฤดูกาล 2026 ไม่ได้อ้างว่าเก็บ HTML หน้านั้นสำเร็จ เม็กซิโกอ่าน crest pairings ใน PDF ที่ render จริง แล้วตรวจชื่อกับ directory ทางการร่วม ชื่อ canonical คือ label ที่ลีก/สมาคมเผยแพร่ ไม่ใช่การรับรองชื่อนิติบุคคลของทุกสโมสร เก็บ native Korean names และไม่สร้าง transliteration ที่ไม่มีหลักฐาน

ตรวจ material changes และ membership ปัจจุบันแล้ว แต่ไม่รับรองประวัติคำสั่งเลื่อนชั้น/ตกชั้นหรือการซื้อขายนิติบุคคลย้อนหลังทุกกรณี รายละเอียดอยู่ใน `evidence/change_review.json` ไม่มีการใช้ความคล้ายชื่อยืนยันว่า Atlante กับ Mazatlán เป็น canonical club เดียวกัน

## D. Provider Readiness

Mapping ใน production สำหรับลีกใหม่นี้: **0 confirmed / 11 unmapped** เตรียม candidates ครบ 11 จาก `reports/master_provider_snapshot.json` ที่เก็บวันที่ 11 ต.ค. 2026 เวลา 14:32:50 UTC พร้อม SHA-256 ต้นทาง ไม่เรียก OddsPapi หรือ endpoint ราคาใด ๆ

| Canonical competition | Candidate tournament ID | Exact provider label |
|---|---:|---|
| JPN-0001 | 196 | J1 League |
| JPN-0002 | 402 | J2 League |
| KOR-0001 | 410 | K-League 1 |
| KOR-0002 | 777 | K-League 2 |
| AUS-0001 | 136 | A-League |
| USA-0001 | 242 | MLS |
| BRA-0001 | 325 | Brasileiro Serie A |
| BRA-0002 | 390 | Brasileiro Serie B |
| ARG-0001 | 155 | Primera LPF |
| MEX-0001 | 27464 | Liga MX |
| SAU-0001 | 955 | Saudi Pro League |

Candidates คือ catalog identity ที่พบจริง ไม่ใช่ mapping ที่เปิดใช้แล้ว เกาหลีอยู่ใน category `Republic of Korea` MLS ใน `USA` ไม่ใช่ประเทศของทุกสโมสร เม็กซิโกมี legacy ID `352` และ Clausura `27466` แยกต่างหาก ห้ามเอา candidate `27464` ไปผูกทุก stage โดยไม่มีหลักฐาน

งานค้างก่อน activation: ยืนยัน season/stage semantics, จับคู่ participant ID ทีละสโมสรด้วยหลักฐานตรง และตรวจ availability ภายใต้ quota ที่ได้รับอนุมัติ ไม่มี team ID ที่เดาไว้ให้ผ่านจำนวน

## E. Safety & QA

Baseline master structural validation: PASS; 81 active divisions VERIFIED_OFFICIAL และ exclusions เดิมครบ 6 รายการ

การตรวจ staging ครอบคลุม duplicate IDs/names/aliases, required fields, foreign keys, canonical redirects, domestic season membership, projection, source roster equality, expected counts, evidence metadata, provider catalog hashes, season stage และ cross-border memberships

Production isolation ใช้สองชั้น: เปรียบเทียบ hash ของ baseline tracked files ทั้ง 715 ไฟล์ และเรียก production allowlist/mapping loader จริงเพื่อยืนยันว่าไม่มี competition ใหม่ในผลลัพธ์ นอกจากนี้ตรวจ source tree ว่าไม่มี staging reader

เปลี่ยนเฉพาะ dataset/evidence/validator ใน research directory, regression tests ใหม่ และรายงานนี้ ไม่มี production files เปลี่ยน ไม่มี workflow เปลี่ยน ไม่มี deployment หรือ workflow dispatch

Full suite เดิมมี test side effect เขียน synthetic local scan-health files; คืน local test outputs เป็น baseline และตรวจ hash ซ้ำก่อน commit ไม่ส่ง test outputs ขึ้น GitHub และไม่แก้ production logic เพื่อแก้ test side effect ในงานนี้

ผลทดสอบ local: full pytest **629 passed**, staging regression **22 passed**, baseline unittest **27 passed**, baseline validator PASS และ staging validator PASS หลังคืน test side effects

**GitHub CI: SKIPPED_FOR_PRODUCTION_ISOLATION — ไม่ใช่ PASS** พบ existing issue: `pages.yml` รับ `workflow_run` ของ `Research V2 Offline Evidence Audit` โดยไม่กรอง event หรือ branch; Offline Evidence Audit รันทุก PR และไม่มี draft guard จึงอาจตามด้วย deployment ของ main แม้ PR ยังไม่ merge ใช้ `[skip ci]` ใน head commit เพื่อไม่ให้ automatic push/PR workflows เริ่ม ตาม [GitHub Docs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs) ไม่แก้ workflow ที่อยู่นอกขอบเขต

ไม่มี CI run URL สำหรับ commit ที่ข้ามการรัน ต้องแยกแก้/อนุมัติ CI isolation ก่อนจึงจะได้ GitHub CI verification ที่ปลอดภัย ข้อจำกัดนี้ไม่เกี่ยวกับความครบถ้วนของ roster แต่ทำให้ **ไม่สามารถรายงานว่าทุก Phase รวม GitHub CI เสร็จสมบูรณ์** ภายใต้ข้อห้ามปัจจุบัน

## F. GitHub

Working branch: `feature/global-master-phase1-20261014`

Draft PR ไปยัง `main` เท่านั้น Commit SHA, PR URL และ CI workflow URL ที่ตรวจจริงอยู่ใน PR description และรายงานส่งมอบ ไม่มี merge / deploy / auto-merge

## G. เสนอ Phase 2

ข้อเสนอต่อไปนี้เป็นลำดับสำหรับวิจัยฐานข้อมูล ไม่ใช่การรับรอง liquidity, live odds coverage หรือความได้เปรียบเดิมพัน ต้องตรวจ roster และ provider evidence ก่อนเพิ่มจริง

| กลุ่มเสนอ | ลีก | ประโยชน์ | ข้อจำกัด / trade-off |
|---|---|---|---|
| South America ต่อเนื่อง | Chile Primera División, Colombia Primera A, Ecuador LigaPro, Uruguay Primera División | ขยายลีกสูงสุดโดยใช้รูปแบบ canonical เดิม | บางประเทศมีหลาย stage; ต้องแยก stage และ annual membership ชัดเจน |
| Asia / Gulf ต่อเนื่อง | China Super League, Qatar Stars League, UAE Pro League, Thai League 1 | เพิ่มช่วงเวลาการแข่งขันเอเชียและลีกระดับสูง | การเปลี่ยนชื่อ/ใบอนุญาต และ provider team identity ต้องตรวจใหม่ |

ประโยชน์ของการคง staging คือทดลองตรวจ data ได้โดยไม่เพิ่มการใช้ quota หรือเปลี่ยน scan universe ข้อเสียคือฐานใหม่ยังใช้สแกนไม่ได้จนกว่าจะทำ migration ที่อนุมัติแยกต่างหาก การมีทีมครบไม่ได้ยืนยันว่าทุกทีมมีตลาดราคาที่ใช้งานได้จริง
