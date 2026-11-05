# MatchLedger Football — 5 พฤศจิกายน 2026
## A. ผลเมื่อวาน — วันฟุตบอล 4 พ.ย.
ตรวจด้วย Fixture ID จาก Ledger ที่บันทึกก่อนเตะและ FT cache ของ Repository ครบ 5/5 รายการ ผลนอก Ledger ที่ยังพิสูจน์เวลาเผยแพร่ไม่ได้ไม่นำมารวม
| คู่ | คำทำนายเดิม | FT | ผล |
|---|---|---|---|
| PSV Eindhoven – Club Brugge | Under 3.5 goals | 1–2 | FULL_WIN |
| RB Leipzig – Manchester City | Under 3.5 goals | 2–3 | FULL_LOSS |
| Fenerbahce Istanbul – Liverpool FC | Fenerbahce Istanbul +1.25 AH | 3–2 | FULL_WIN |
| KV Kortrijk – Yellow-Red KV Mechelen | Yellow-Red KV Mechelen +0.25 AH | 1–3 | FULL_WIN |
| Bristol City – Wolverhampton Wanderers | Bristol City +0.25 AH | 1–2 | FULL_LOSS |

| ตลาด | Daily WR | Cumulative WR | FW | HW | Push | HL | FL | Pending |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AH | 66.67% | 66.67% | 2 | 0 | 0 | 0 | 1 | 0 |
| OU | 50.00% | 50.00% | 1 | 0 | 0 | 0 | 1 | 0 |

WR = (FW + 0.5 HW)/(FW + 0.5 HW + FL + 0.5 HL) ไม่รวม Push/Pending. Cumulative ครอบคลุมประวัติ Ledger ที่พบเพียง 1 วัน (4 พ.ย.) จึงยังประเมินความแม่นยำระยะยาวไม่ได้ Coverage ผล 100% ของ 5 รายการใน archive ไม่ใช่ยืนยันว่ากู้คืนทุกคำทำนายจากทุกแชทครบแล้ว ไม่พบรายการวันที่ 4 พ.ย. เพิ่มจากการค้นบริบทแชทที่เข้าถึงได้ และไม่นำ recap วันที่ 3 พ.ย. มารวมย้อนหลัง

## B. วันนี้ — EDITORIAL_RESEARCH_LEAN ทั้งหมด
| Kickoff UTC (2026-11-05) | ลีก | คู่ | Pick | ระดับ | เหตุผล / Historical weighted WR และ N |
|---|---|---|---|---|---|
| 17:45 | UEFA Europa League | Lillestroem SK – FC Viktoria Plzen | FC Viktoria Plzen -0.25 AH | CAUTIOUS | S1 กลุ่มไลน์ 55.34% N=323; กลุ่มราคา 61.84% N=84; S4 บริบท AH×OU ผลตอบแทนบวก 53.33% N=30 |
| 17:45 | UEFA Conference League | Trabzonspor – SC Freiburg | Trabzonspor +0 AH | CAUTIOUS | S1 กลุ่มไลน์ 57.02% N=170; กลุ่มราคา 56.47% N=115; S4 บริบท AH×OU ผลตอบแทนบวก 57.14% N=21 |
| 20:00 | UEFA Conference League | AS Monaco – FC Nordsjaelland | AS Monaco -1.25 AH | CAUTIOUS | S1 กลุ่มไลน์ 56.39% N=170; กลุ่มราคา 57.83% N=46; S4 บริบท AH×OU ผลตอบแทนบวก 57.58% N=33 |

ผลตอบแทนบวกในบริบท S4 ใช้นิยามเดิมของ Dashboard (FW+HW)/N รวม Push ไม่ใช่ weighted WR จึงแสดงแยก ไม่ตีความเป็นตัวเลขเดียวกัน

- Plzen: สถิติของทีมเยือนต่อ -0.25 และ price band [2.00,2.10) ไปในทิศทางเดียวกัน แต่บริบท OU 3.0 มีเพียง 30 คู่
- Trabzonspor: กลุ่มเจ้าบ้านไลน์ 0 กับ price band [1.80,1.90) สนับสนุนทิศทางเดียวกัน แต่บริบท OU 3.0 มีเพียง 21 คู่
- Monaco: กลุ่มเจ้าบ้านต่อ -1.25 กับ price band [1.80,1.90) สนับสนุนกัน บริบท OU 3.25 มี 33 คู่ ยังเป็นกลุ่มเล็ก
- S2 และ S3: ตรวจ OU ทุกรายการแล้ว ไม่เลือก OU เพราะไม่ผ่านเกณฑ์สนับสนุนร่วมที่ใช้ในการคัดบรรณาธิการของฉบับนี้

## C. Data Integrity
- รอบ 15:00 ไทย สังเกตจริง 15:00:47.309046 (08:00:47 UTC) ล่าช้าประมาณ 0.11 นาที ตาม Slot Ledger
- 36 fixtures ที่พบ / 35 strict snapshots (97.22%); collection_succeeded=true, coverage_complete=true ในใบรับรอบสแกน ไม่ตีความว่าได้ราคาครบ 100%
- วิเคราะห์ 35 คู่ที่มีราคาและยังไม่เริ่ม ณ เวลาบันทึก; 3 AH picks, 0 OU picks; ไม่เติมอีก 1 คู่ด้วย API
- Scan Health วันนี้ WARNING, API errors=0; ใบรับรอบสแกนพบ 38 fixtures / market response 36 / valid odds 35 / without valid odds 3. Slot ledger ของวันฟุตบอลวันนี้ระบุ 36 fixtures และ 35 strict snapshots; ตัวหารสองชุดไม่ตรงกัน โดย competition coverage ยืนยันตาราง 36 คู่ (Conference 18 / Europa 17 / Liga II 1); ยังไม่ได้ตรวจแยกส่วนต่าง discovery 2 รายการในงานสื่อ จึงไม่เรียก 35/36 ว่าครอบคลุมทุก fixture ที่พบ (35/38 = 92.11% ของ scan-health discovery). รายงาน monitor ที่อ่านก่อนหน้านี้ยังค้างวันที่ 4 พ.ย.
- ใช้สถิติที่สร้าง 2026-11-05T03:02:32Z ก่อนรอบราคาและก่อนบันทึก ไม่มี FT ของคู่วันนี้ในสถิติ
- Snapshot source commit: 8a8c20f989486376176256648c317d9a9c6c488a; อ้าง main ที่ตรวจล่าสุด e0ee319f6650f7dbdb15020fd7b80f29c9891556
- Ledger timestamp จริง: 2026-11-05T08:45:50.353616+00:00; ทุกคู่ยังไม่เตะ ณ เวลานี้
- ประวัติและผล FT มาจาก cache ที่มีอยู่ ไม่ได้ตรวจเว็บผลบอลสดซ้ำหรือเรียก API บอลใหม่
- ทั้ง 3 คู่เป็นฟุตบอลยุโรป แต่กลุ่มอ้างอิงรวมหลายลีก ยังไม่มีหลักฐานเฉพาะ Europa/Conference League ว่าจะทำซ้ำได้

## ข้อจำกัดและเกณฑ์คัดฉบับนี้
การคัด AH ใช้กลุ่มไลน์ N≥100 และ weighted WR≥55%, กลุ่มราคา N≥40 และ weighted WR≥55%, บริบท AH×OU N≥20 และ positive-return event rate≥53%. OU ใช้กลุ่มไลน์/ราคา N≥60 และกลุ่ม AH×OU N≥30 พร้อม weighted WR ทิศเดียวกัน ≥55% ทั้งคู่ เกณฑ์นี้เป็นตัวกรองบรรณาธิการที่บันทึกไว้สำหรับฉบับนี้ ไม่ใช่การรับรองเชิงสถิติหรือปรับ Frozen Validation Gates

ประโยชน์: เห็นเหตุผลและขนาดตัวอย่างที่ตรวจย้อนกลับได้ ข้อเสีย/ความเสี่ยง: เลือกจากหลายกลุ่มอาจเกิด selection bias และกลุ่มซ้อนทับกัน ใช้เป็นหลักฐานอิสระไม่ได้ กลุ่มบริบทเล็กและ pooled leagues ทำให้ความไม่แน่นอนสูง Historical WR ไม่ใช่โอกาสชนะของคู่วันนี้ ไม่มีการทดสอบนัยสำคัญหรือยืนยัน ROI/edge เพิ่มในงานนี้

## สถานะการผลิต
มี MP4 จริง 4 คลิป: Full 238.337 วินาที และ Shorts 18.033 / 18.700 / 18.304 วินาที พร้อมซับ ภาพปก และ metadata แยกคลิป ตรวจ decode และเฟรมจริง พร้อมแก้ footer ที่ทับซับใน Full และตรวจผลใหม่ ไม่มีการอัปโหลด YouTube ดูรายละเอียด QA ใน qa-report.md

คู่ในตารางที่ไม่มี strict snapshot: Fixture ID `id1003448074173284` (Conference League) ไม่เดาชื่อทีมและไม่ออกคำทำนายจากข้อมูลที่ขาด
