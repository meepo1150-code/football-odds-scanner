# MatchLedger Football — Episode 6 พฤศจิกายน 2026

## ผลเมื่อวาน — วันฟุตบอล 5 พฤศจิกายน

| คู่ | Prediction เดิม | FT | Settlement |
|---|---|---|---|
| Lillestrom – Viktoria Plzen | Plzen -0.25 AH | 0–1 | FULL_WIN |
| Trabzonspor – Freiburg | Trabzonspor 0 AH | 0–1 | FULL_LOSS |
| Monaco – Nordsjaelland | Monaco -1.25 AH | 2–0 | FULL_WIN |

ตรวจ Prediction ก่อนเตะจาก hash-chained ledger และผล FT cache ด้วย Fixture ID ตรงกันครบ 3/3 ผลจาก Flashscore exact external ID ที่ระบบหลักบันทึกไว้ ไม่ได้เรียก Football API ใหม่ ข้อมูล cache มี explicit FT และ final-score provenance; งานนี้ไม่ได้ตรวจหน้าเว็บผลบอลสดซ้ำ

| ขอบเขต | ตลาด | Settlement-weighted WR | N | FW | HW | Push | HL | FL | Pending |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| เมื่อวาน | AH | 66.67% | 3 | 2 | 0 | 0 | 0 | 1 | 0 |
| เมื่อวาน | OU | N/A | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| สะสม 4–5 พ.ย. | AH | 66.67% | 6 | 4 | 0 | 0 | 0 | 2 | 0 |
| สะสม 4–5 พ.ย. | OU | 50.00% | 2 | 1 | 0 | 0 | 0 | 1 | 0 |

WR = (FW + 0.5 HW) / (FW + 0.5 HW + FL + 0.5 HL) ไม่รวม Push/Pending เป็น Settlement-weighted WR ไม่ใช่อัตราชนะเต็ม ไม่ใช่ ROI และไม่ใช่โอกาสชนะรายแมตช์ กลุ่มนี้ไม่มีผลครึ่งจึงตัวเลขตรงอัตราชนะเต็มโดยบังเอิญ

ค้นบริบทแชทเพิ่มเติมแล้ว ไม่พบหลักฐาน Main/Additional/Reserve วันที่ 5 พ.ย. นอกเหนือจาก 3 คู่นี้ แต่ไม่สามารถรับรองว่ากู้คืนทุกข้อความจากทุกแชทได้ครบ ไม่สร้างประวัติย้อนหลังและไม่รวม reconstructed chat history ในสถิติสะสม ประวัติสะสมมีเพียง 2 วัน ยังใช้วัดความแม่นยำระยะยาวไม่ได้

## Prediction วันนี้

ทุกคู่เป็น EDITORIAL_RESEARCH_LEAN / CAUTIOUS ไม่มี VALIDATED_EDGE บันทึกจริง 2026-11-06 11:29:52 UTC (18:29:52 ไทย) ก่อน kickoff ทั้งหมด

| Kickoff UTC | ลีก | คู่ | Pick | หลักฐานสถิติ |
|---|---|---|---|---|
| 2026-11-06 17:00 | Czech National Football League | Jihlava – Karvina | Jihlava 0 AH | S1 ไลน์ 57.02% N=171; price cohort 56.47% N=116; S4 positive-return event rate 57.14% N=21 |
| 2026-11-06 17:00 | Danish 1st Division | Vejle – Fredericia | Vejle 0 AH | S1 ไลน์ 57.02% N=171; price cohort 60.00% N=54; S4 positive-return event rate 57.14% N=21 |
| 2026-11-06 19:00 | Eredivisie | Willem II – PEC Zwolle | Under 3.0 | S2 weighted WR 55.43% N=113; S3 AH×OU weighted WR 70.00% N=31 |
| 2026-11-06 19:30 | FA Cup | Bristol Rovers – Cambridge United | Under 3.0 | S2 weighted WR 55.43% N=113; S3 AH×OU weighted WR 70.00% N=31 |

AH: ทั้งสองคู่มีโครงสร้างเจ้าบ้านไลน์ 0 และ OU 3 เหมือนกัน กลุ่มไลน์ S1 ใหญ่กว่าและสนับสนุนทิศทางเดียวกับ price cohort: Jihlava ใช้ band 1.80–1.89, Vejle ใช้ 1.90–1.99 จุดแข็งคือไม่อาศัยเปอร์เซ็นต์จากกลุ่มเล็กเพียงอย่างเดียว แต่ S4 มีเพียง 21 คู่ และเป็น positive-return event rate (FW+HW)/N รวม Push ไม่ใช่ weighted WR จึงไม่ควรเอา 57.14% ไปเฉลี่ยกับ WR อีกสองค่า

OU: ทั้งคู่มีทีมเยือนต่อ -0.25 และ total 3.0 เหมือนกัน S2 ใช้ total/over-price cohort 1.90–1.99 และ S3 ใช้โครงสร้าง AH×OU สนับสนุน Under เหมือนกัน แต่ 70% มาจาก 31 คู่เท่านั้น ขณะที่กลุ่มใหญ่กว่าได้ 55.43% จึงไม่อ้างว่าโอกาสออกต่ำของแต่ละคู่คือ 70%

ประโยชน์ของการคัดนี้คือหลักฐานและขนาดตัวอย่างตรวจย้อนกลับได้ ข้อเสีย/ความเสี่ยงคือทุกกลุ่มรวมหลายลีกและซ้อนทับกัน ทั้ง 2 AH ใช้ line/context cohort ร่วมกัน และทั้ง 2 OU ใช้ cohort เดียวกันทั้งหมด จึงเสี่ยงไปในทิศทางเดียวกัน ไม่ใช่หลักฐานอิสระ ไม่มีการวิเคราะห์รายชื่อนักเตะ ข่าวล่าสุด หรือความได้เปรียบเฉพาะลีกเพิ่มเติมเพราะงานนี้จำกัดข้อมูลจากระบบที่บันทึกไว้

## Data Integrity

- Source main commit: `309b0705a26705199ce7bccaef0109cdfbd73c58`
- สถิติสร้าง 2026-11-06 03:03:43 UTC ก่อนรอบสแกน 15:00 ไทย ไม่ใช้ผลหลัง Snapshot มาคัดย้อนหลัง
- Target 15:00:39 ไทย, collection completed 15:01:08.603115 ไทย / 08:01:08 UTC; Snapshot รายคู่มี timestamp จริงต่างกัน
- Slot Ledger: market-response fixtures 91, strict snapshots 90 (98.90% ของ response cohort) collection_succeeded=true และ coverage_complete=true หมายถึงคำขอครบ ไม่ใช่มีราคาครบทุกคู่
- Health ของรอบ 15:00 จาก commit `1845e8a9374b3cafb1961b3f58e229d9d2d67ce6`: WARNING, discovery 99, market response 91, valid strict core-AH odds 85, API errors 0 ตัวหารต่างกัน จึงห้ามเรียก 90/91 ว่าครอบคลุมตลาดทั้งหมด
- Reviewed 90 snapshots; 86 คู่ยังไม่เริ่ม ณ เวลาบันทึก; 4 คู่เริ่มแล้วจึงตัดออก; คัด 4 picks (AH 2 / OU 2) ไม่มีเพดานจำนวนคู่
- 1 response fixture ไม่มี strict snapshot ไม่เดาราคาเติม Discovery/health ที่ไม่ผ่านและคู่ไม่มี market response แยกตามหลักฐานใน scan-evidence.json; ไม่ใช้รอบ 18:00 แทน
- รายการที่ไม่เลือกทุกรายการพร้อม evidence และเหตุผลอยู่ใน all-fixture-analysis.json
- เกณฑ์บรรณาธิการเดิม: AH baseline N≥100/WR≥55%, price N≥40/WR≥55%, context N≥20/positive-return≥53%; OU N≥60 และ context N≥30 โดย weighted WR≥55% ทั้งสองกลุ่ม เกณฑ์นี้ไม่ใช่ Frozen Validation Gates และไม่มีการลดเกณฑ์หลัก
- Ledger ตรวจ hash chain ผ่าน; timestamp จริงมาจาก system clock; manifest เก็บ Fixture ID/ลีก/เวลา/market/line/evidence/source commit/snapshot hash ไม่ backdate หรือเปลี่ยน Prediction เดิม
- เลือก Shorts: Vejle (price WR 60%, N=54), Jihlava (price N=116), Willem II (OU N=113) ไม่ทำ Bristol ซ้ำเป็น Short ลำดับที่ 4 เพราะ Under ทั้งสองใช้หลักฐานเดียวกัน

## สถานะงาน

รายละเอียดการเรนเดอร์และ QA ของ MP4 ฉบับสุดท้ายรายงานใน qa-report.md และ media-qa.json ไม่มีการแก้ Auto Scan, Manual Scan, secrets, quota, Dashboard หรือ Statistical Engine และไม่มีการอัปโหลด YouTube
