from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import math
p=Path('assets');p.mkdir(exist_ok=True);w,h=1280,720;im=Image.new('RGB',(w,h),'#14201E');d=ImageDraw.Draw(im)
for y in range(h):
 col=tuple(int(c*(1-y/h*.3)) for c in (20,32,30));d.line((0,y,w,y),fill=col)
d.polygon([(780,0),(1280,0),(1280,720),(620,720)],fill='#203C30');d.line((810,70,1180,70,1180,650,810,650,810,70),fill='#447455',width=3);d.ellipse((870,260,1130,520),outline='#447455',width=3);d.line((810,390,1180,390),fill='#447455',width=3)
f='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';reg='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def t(x,y,text,size,color='#E8E6DF'):
 font=ImageFont.truetype(f,size)
 while d.textbbox((0,0),text,font=font)[2]>1160-x: size-=1;font=ImageFont.truetype(f,size)
 d.text((x,y),text,font=font,fill=color)
t(55,42,'MATCHLEDGER FOOTBALL',35,'#D7FA55');t(55,105,'05 NOV 2026 / FOOTBALL PREDICTIONS',26)
t(48,180,'3 AH LEANS',115,'#D7FA55');t(55,330,'MONACO',72);t(55,423,'PLZEN + TRABZONSPOR',55)
d.rounded_rectangle((50,550,1200,632),radius=12,fill='#D7FA55');t(75,563,'YESTERDAY: EVERY RESULT',39,'#14201E');t(55,664,'Every Pick. Every Result. / CAUTIOUS RESEARCH',22)
im.save(p/'matchledger-thumbnail-2026-11-05.png')
