# ปิดช่องว่างก่อนตรวจรอบ 15:00 — 15 ตุลาคม 2026

## สถานะจริง

งานนี้ไม่ใช่ชุดสาม และไม่เพิ่มลีกหรือสโมสรใหม่
ขอบเขตยังเป็น 33 ลีก / 588 สโมสรใน staging; production master เดิม 81 ลีก / 1,203 ทีม

- จาก PR #376: 24/33 competition identities และ 270/588 participant identities
- ผลล่าสุด: **26/33 competition identities และ 300/588 participant identities** เพิ่ม 2 ลีก/30 ทีม
- เหลือ 7 competition identities และ 288 participant identities ที่หลักฐานไม่พอ
- Team ID ของเราเองยังครบ 588 ทีม; ไม่ใช้ Provider ID แทน canonical ID
- Mapping นี้ยังไม่ใช่การยืนยัน provider season/stage หรือความพร้อมราคาปัจจุบัน
- ไม่มีการเปิดลีกใหม่เข้า production scan หรือเปลี่ยน daily cohort

7 ลีกที่ยัง REVIEW: UAE Pro League, Argentina Primera División/Primera Nacional,
Bolivia División Profesional, Brazil Série B, Colombia Primera A และ Korea K3
ต้องคงรายการค้างไว้ ไม่สร้าง ID/alias เพื่อให้ครบเป้า และยังพักการขยายชุดสาม

## หลักฐานใหม่

1. K League native/English club profiles อ้าง `teamId` เดียวกันครบ 29 สโมสร
   ดึงชื่อเฉพาะ `sub-top club Kxx` ไม่ใช้ชื่อทีมจาก navigation ของทั้งเว็บไซต์
   ภาษาอังกฤษใช้ public `changeLang.do` session preference ของเว็บทางการ
   ไม่สร้าง transliteration; K02 Suwon Samsung แยก K29 Suwon FC
   K05 Jeonbuk ชุดใหญ่ใช้เฉพาะ K League1 ไม่ผูกกับ K3 reserve/N squad
2. คำว่า Football Club ท้ายชื่อทางการเทียบกับ FC ได้ โดยตัดเฉพาะวลี legal designator
   ท้ายชื่อ ไม่ลบเมือง Saudi ชื่อทีมสำรอง หรือตัวเลข เช่น Gimcheon Sangmu Football Club
3. Ministry of Media/Saudipedia ระบุ Al-Khaleej Club และ Al-Nassr Club
4. เว็บไซต์สโมสร Al Ahli ระบุ Al Ahli Saudi Football Club; คงคำ Saudi ไว้
5. SPL fixture URL `al-hazem-vs-al-ahli` และ commentary ของแมตช์เดียวกันใช้ Al-Hazm
6. Thai League public API tournament 177 แสดง UTTARADIT SAKSIAM FC ที่ club_id=47
   ตรงกับ stable official club_id ของ UTTARADIT FC ในทะเบียน 2026/27 เดิม
   ใช้ยืนยันชื่อเก่าเท่านั้น ไม่เอาสมาชิก/ฤดูกาลเก่ามาแทนปัจจุบัน

หลักฐาน factual extracts, UTC timestamps และ response SHA256 อยู่ในสองไฟล์ official_aliases
builder pin SHA256 และยังใช้ paired fixtures/catalog gates เดิม ไม่ใช้ fuzzy matching
ไม่รับรอง Seongnam Ilhwa หรือชื่อ predecessor ที่ไม่มีหลักฐานความต่อเนื่อง

## การตรวจรอบ 15:00

Cached preview วันที่ 11 ต.ค. มีคู่วันที่ 15 ต.ค. 6 คู่: Saudi Pro League 4 คู่ และ Thai League2 2 คู่
หลังแก้จับคู่ทั้งสองทีมได้ 6/6 แต่ **ไม่ใช่ผลสดหรือผลทดสอบราคา**

Readiness audit จะอ่าน `/fixtures` response จริงที่ canonical collector เก็บหลัง 15:00
ตรวจทุกลีกทั้ง 33 รายการ โดยไม่ส่ง request ซ้ำ และรายงาน ID ที่ขาดแยกรายทีม/คู่
ต้องตรง provider namespace, football-day window, tournament identity, participant IDs,
current roster และ provider names; version ขัดแย้งกัน fail closed
คำตอบถึง limit หรือมี pagination ไม่ใช้รับรองความครบ
ไม่มี fixtures กลับมาไม่เท่ากับไม่มีการแข่งขันหรือ API ไม่รองรับ

การทดสอบราคาชุดขยายเป็น shadow probe แยก ไม่เปลี่ยนวงสแกนหลัก:

- ทำเฉพาะวันที่ 15 ต.ค. 2026 หลังรอบ 15:00 และภายใน 90 นาที
- ทุก expansion fixture ที่ response ส่งกลับมาต้องจับคู่ครบทั้งสองทีมก่อน
- เลือกเฉพาะคู่ยังไม่เตะ; ใช้ verified competition IDs รวมไม่เกิน 5 ลีก
- ไม่ตัดเหลือบางลีกเพื่อรายงานว่าครบ หากเกินหนึ่ง batch ให้ BLOCKED
- ตรวจ account จริงและ reserve shared UTC quota บน main ก่อนยิง API
- ใช้ได้สูงสุด 1 metered request ไม่มี retry และกันรอบ 18/21/00 ตาม allocator เดิม
- หาก mapping ไม่ครบ โควต้าไม่พอ หรือ schedule ไม่สมบูรณ์ จะไม่ยิงราคา
- ใช้ strict mainLine=true, active bookmaker/markets, AH/OU/1X2 extractor เดิม
- เก็บ raw response และ normalized shadow snapshots เป็น artifact; ไม่เขียนราคาลง production history

การขอราคาครบทั้ง 33 ลีกต้องไม่น้อยกว่า 7 batches แต่ optional grant ก่อน 15:00 มีเพียงหนึ่ง
ดังนั้น full-scope live test ยัง BLOCKED ทั้ง mapping และ quota
probe นี้ตรวจได้เฉพาะชุดคู่ที่ API คืนมาของวันนั้น ไม่ได้พิสูจน์ครบทั้ง 588 สโมสร

## ความปลอดภัยและการตรวจสอบ

- Readiness workflow เป็น contents:read ไม่มี secret หรือ provider transport
- Probe workflow รันหลัง Daily Preparation Scan ที่เป็น schedule/main/repository เดียวกัน
  serialize กับ research-v2-collectors และมี date/time guard; ไม่แก้ scheduler เดิม
- Probe เขียนเฉพาะ new status report และ quota reservation; ไม่แก้ master mapping/ราคา/FT/fixture history
- Full pytest, master unittest, official rebuild และ remote CI ต้องผ่านก่อน merge
- ตัวเลขผล tests, CI URLs, merge SHA และ post-merge verification บันทึกใน PR
- Job SUCCESS แปลว่า audit ทำงาน ไม่แปลว่า mapping ครบหรือ Scan Health PASS

ข้อดี: ได้ตรวจ actual API payload และราคาอย่างมีขอบเขต โดยไม่กินโควต้าซ้ำกับ fixture discovery
ข้อจำกัด: คู่ที่ API ไม่ส่งกลับมาและทีมที่ยังไม่ปรากฏใน fixtures ไม่ได้รับการรับรอง
ความเสี่ยง: API อาจไม่มีตลาด หรือ quota ถูก job อื่นใช้ก่อน; guard ต้องรายงาน BLOCKED/SKIPPED_QUOTA ตามจริง

## Local validation ของชุดสุดท้าย

826 pytest tests ผ่าน (154.40s); master unittest 27 tests ผ่าน (82.155s)
official identity rebuild และ audit CLI ผ่าน; probe CLI ก่อน 15:00 รายงาน WAITING_1500_SCAN
และ provider_requests_attempted=0 ตามจริง
Existing protected production paths SHA256 ตรง 361/361 หลังคืน diagnostics จาก tests
ไม่มีการแก้ tests/guards เดิมเพื่ออนุญาต staging reader ใน Production
