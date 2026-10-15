# ตรวจชื่อทางการต่อจาก PR #375 — 15 ตุลาคม 2026

## ผลและข้อจำกัด

เพิ่มหลักฐานชื่อเต็มที่ผูกกับชื่อย่ออย่างชัดเจนจากเว็บสมาคม APF/ AUF
โดยไม่เปลี่ยนเกณฑ์ขั้นต่ำสอง fixtures/สี่สโมสร และต้องตรงทั้งสองฝ่ายกับ participant catalog

| รายการ | PR #375 | ผลรอบนี้ |
|---|---:|---:|
| Cached competition identity | 22/33 | 24/33 |
| Cached participant identity | 253/588 | 270/588 |
| Competition REVIEW | 11 | 9 |
| Club UNRESOLVED | 335 | 318 |
| Provider requests ของงานนี้ | 0 | 0 |
| Season/stage verified | 0 | 0 |
| Production activation | false | false |

สองลีกที่ผ่านเพิ่ม: PRY-0001 ใช้ cached tournament 27098 มี 8 paired fixtures/9 สโมสร;
URY-0001 ใช้ 278 มี 7 paired fixtures/8 สโมสร รวม 17 สโมสรผ่านเพิ่มจริง
ไม่ได้อ้างว่าทั้งสองลีกมี participant mapping ครบทุกทีม
ไม่มีการเพิ่มการแข่งขัน สมาชิก หรือ canonical IDs; จำนวนฐานข้อมูลเดิมไม่เปลี่ยน

## หลักฐานและการตัดสิน

- APF https://www.apf.org.py/ — JSON `__NEXT_DATA__` มี `name`, `shortName`,
  `nickname` ภายใต้ team UUID เดียวกันสำหรับ 12 สโมสร เช่น Sportivo Amel. กับ
  Sportivo Ameliano; ใช้ชื่อจาก fields จริง ไม่มีการขยายคำย่อด้วยการเดา
- AUF https://www.auf.org.uy/liga-auf-uruguaya/ — link ของ Def. Sporting,
  Nacional, D. Maldonado และ M.C. Torque ผูกกับหน้า profile ผู้ชายโดยตรง
- https://www.auf.org.uy/defensor-sporting-club/
- https://www.auf.org.uy/club-nacional-de-football/
- https://www.auf.org.uy/deportivo-maldonado-s-a-d/
- https://www.auf.org.uy/montevideo-city-torque-f11/

หน้า `/montevideo-city-torque/` เป็นทีมหญิง จึงปฏิเสธและใช้ link ที่ตารางลีกชายระบุจริง
เก็บ factual identity extracts, retrieval timestamps และ raw-response SHA256 ใน
`data/research/global_provider_alias_followup/evidence.json`; builder pin hash ป้องกัน
การเปลี่ยนหลักฐานโดยไม่ review ต้นทาง ไม่มี fuzzy match หรือลบคำระบุทีมสำรองเพิ่ม

ผลใหม่อยู่ใน directory follow-up แยกจากรายงาน #375 เดิม เพื่อรักษา baseline ที่ตรวจย้อนหลังได้
ตัว reviewer เดิมเพิ่มเพียง optional scoped alias input; การเรียกเดิมยังได้ผลเดิมทุกระเบียน
รายการค้างรายสโมสรทั้ง 33 ลีกอยู่ใน `review.json` ช่อง `remaining_work`

## งานที่ยังต้องมีหลักฐาน

9 competition identities: UAE, Argentina Primera/Primera Nacional, Bolivia,
Brazil Série B, Colombia, Korea K1/K2/K3; รวม 318 participant identities ยังไม่ผ่าน
ผลรอบนี้ไม่ถือเป็นหลักฐาน provider season/stage, bookmaker availability หรือ live odds coverage
ชื่อ provider ที่ไม่พบในหลักฐานทางการยังคง UNRESOLVED; ไม่เดา ID หรือเติม alias เพื่อให้ครบ
ก่อน activation ต้องมี PR แยกยืนยัน season/stage, roster coverage, ตลาด, quota และ rollback
ประโยชน์ของงานนี้คือปิดความกำกวมของชื่อเพิ่มโดยไม่มีค่า API;
ข้อจำกัดคือ cache วันที่ 11 ต.ค. ไม่สามารถพิสูจน์ความพร้อมราคา ณ ปัจจุบันได้

## Validation และ Production isolation

รัน full pytest, master unittest และ deterministic staging rebuild ก่อน merge;
ตัวเลขผลทดสอบ/CI และ merge SHA สุดท้ายอยู่ใน PR
Regression ครอบคลุม evidence tampering, source host substitution, membership namespace,
missing fixtures/catalog, unchanged verified IDs, women's profile exclusion และ activation=false

ไม่แก้ scanner, scheduler, workflow, quota, production master, Dashboard หรือ odds/FT history
เปรียบเทียบ SHA256 ไฟล์ Production 361 paths กับ main ที่ตรวจจริง `e6557ceb6985401c873b14888f6f568357e74770`
หลัง tests ต้องคืนเฉพาะ diagnostics ที่ tests สร้างก่อนเปรียบเทียบ hash
ไม่ dispatch scan หรือ Pages deployment ในงานฐานข้อมูลนี้

Local validation: 784 pytest tests ผ่าน (113.86s), master unittest 27 tests ผ่าน (70.070s),
original/supplemental deterministic rebuild ผ่าน และ Production SHA256 ตรง 361/361 paths
หลังคืน diagnostics จาก tests; Dashboard HTML/scan-health/deployment ตอบ HTTP 200 ก่อน PR
