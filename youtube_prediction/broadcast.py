"""Editorial football show: varied broadcast layouts, UTC, timed narration.
Consumes only reviewed episode artifacts; never creates football predictions.
"""
import asyncio
import hashlib
import json
import math
import subprocess
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
from .pipeline import probe,run,stamp
from .engine import read_ledger,settle
from .edition_contract import validate_edition

W,H=1920,1080
PAPER='#E8E6DF'; INK='#14201E'; MUTE='#68706A'; LIME='#D7FA55'; RED='#E96850'; GREEN='#21745C'
FONT='/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf'
BOLD='/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf'
NARROW='/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf'
ALIASES={'Fenerbahce Istanbul':'Fenerbahçe','Liverpool FC':'Liverpool','KV Kortrijk':'Kortrijk','Yellow-Red KV Mechelen':'Mechelen','PSV Eindhoven':'PSV','RB Leipzig':'RB Leipzig','Manchester City':'Man City','Wolverhampton Wanderers':'Wolves','Watford FC':'Watford','Northampton Town':'Northampton','Oldham Athletic':'Oldham','Charlton Athletic':'Charlton','Bolton Wanderers':'Bolton','Queens Park Rangers':'QPR','Burnley FC':'Burnley','FC Shakhtar Donetsk':'Shakhtar','Portsmouth FC':'Portsmouth','Swansea City':'Swansea','Derby County':'Derby','Norwich City':'Norwich','Huddersfield Town':'Huddersfield','Luton Town':'Luton'}
COLORS={'PSV':('#CF2836','#F5F4EE'),'Club Brugge':('#1685D0','#152020'),'RB Leipzig':('#EFEFE8','#DB3748'),'Man City':('#70BDE1','#EEF0E8'),'Fenerbahçe':('#F3D13A','#19345C'),'Liverpool':('#BE2438','#E64552'),'Kortrijk':('#CC273A','#F7F4EE'),'Mechelen':('#E7BA28','#BB3038'),'Bristol City':('#D42B3E','#F2F2E9'),'Wolves':('#EBAF29','#1E2526')}

def short(name):return ALIASES.get(name,name)
def text(d,xy,value,size=48,fill=INK,bold=False,width=None,anchor=None):
    face=NARROW if bold else FONT
    f=ImageFont.truetype(face,size)
    while width and d.textbbox((0,0),str(value),font=f)[2]>width and size>24:
        size-=2;f=ImageFont.truetype(face,size)
    if width and d.textbbox((0,0),str(value),font=f)[2]>width:raise ValueError('Text overflows: '+value)
    d.text(xy,str(value),font=f,fill=fill,anchor=anchor)

def pill(d,box,value,bg=LIME,fg=INK,size=26):
    d.rounded_rectangle(box,radius=8,fill=bg);text(d,((box[0]+box[2])/2,(box[1]+box[3])/2),value,size,fg,True,box[2]-box[0]-18,'mm')

def base(section,dark=False):
    im=Image.new('RGB',(W,H),INK if dark else PAPER);d=ImageDraw.Draw(im)
    color=PAPER if dark else INK
    d.line((68,110,1852,110),fill='#536059' if dark else '#B8BEB5',width=2)
    text(d,(94,42),'TOUCHLINE / DAILY',34,color,True)
    text(d,(1850,60),'04 NOV 2026  •  ALL TIMES UTC',26,color,False,anchor='rm')
    d.rectangle((68,42,78,77),fill=LIME if dark else GREEN)
    text(d,(70,141),section,25,LIME if dark else GREEN,True)
    text(d,(70,1025),'INDEPENDENT FOOTBALL PREVIEW',21,'#929B94' if dark else MUTE)
    text(d,(1850,1025),'08:00 UTC SCAN  /  04 NOV',21,'#929B94' if dark else MUTE,anchor='ra')
    return im

def pitch(d,box,color='#CBD0C5'):
    x,y,x2,y2=box;mid=(x+x2)/2;cy=(y+y2)/2
    d.rectangle(box,outline=color,width=3);d.line((mid,y,mid,y2),fill=color,width=3)
    d.ellipse((mid-80,cy-80,mid+80,cy+80),outline=color,width=3)
    d.rectangle((x,cy-145,x+130,cy+145),outline=color,width=3)
    d.rectangle((x2-130,cy-145,x2,cy+145),outline=color,width=3)

def shirt(d,cx,cy,name,scale=1):
    c1,c2=COLORS.get(name,('#9DADB3','#F5F3E9'))
    pts=[(-65,-115),(-140,-65),(-105,10),(-72,-6),(-72,145),(72,145),(72,-6),(105,10),(140,-65),(65,-115),(30,-92),(-30,-92)]
    pts=[(cx+int(x*scale),cy+int(y*scale)) for x,y in pts]
    d.polygon([(x+8,y+12) for x,y in pts],fill='#BFC3B7');d.polygon(pts,fill=c1)
    d.rectangle((cx-24*scale,cy-90*scale,cx+24*scale,cy+142*scale),fill=c2)
    d.ellipse((cx-32*scale,cy-119*scale,cx+32*scale,cy-77*scale),fill=PAPER)
    # Monogram is an original label, never an official club crest.
    d.rounded_rectangle((cx+30*scale,cy-40*scale,cx+62*scale,cy-8*scale),radius=3,fill=INK)

def pick_label(p):
    if p['market']=='OU':return p['selection']+' '+f"{p['line']:g}"
    team=p['home'] if p['selection']=='HOME' else p['away']
    return short(team).upper()+' '+f"{p['line']:+g}"

def card(scene,path):
    kind=scene['kind'];dark=kind in ('hook','choice','end')
    im=base(scene.get('section','MATCHDAY BRIEFING'),dark);d=ImageDraw.Draw(im)
    if kind=='hook':
        text(d,(90,218),'BIG NAMES.',146,PAPER,True)
        text(d,(90,370),'SMALL MARGINS.',146,LIME,True)
        text(d,(95,575),'Five leans. Every result accounted for.',50,PAPER)
        for i,v in enumerate(['FENERBAHÇE +1.25','PSV UNDER 3.5','CITY GAME: UNDER 3.5']):
            pill(d,(90+i*575,735,635+i*575,825),v,LIME if i==1 else '#31443C',INK if i==1 else PAPER,32)
        # Caption safe area starts below y=875.
    elif kind=='record':
        text(d,(85,220),'YESTERDAY, IN FULL.',105,INK,True)
        for i,(num,lab,col) in enumerate([('2','WINS',GREEN),('6','LOSSES',RED),('8','TOTAL PICKS',INK)]):
            x=90+i*590;d.rounded_rectangle((x,390,x+545,750),radius=14,fill='#F6F4EE')
            text(d,(x+40,414),num,205,col,True);text(d,(x+43,670),lab,37,INK,True)
        text(d,(95,808),'Includes the reserve + both additional selections.',38,MUTE)
        text(d,(95,335),'Reconstructed chat recap • tracked ledger begins today',26,MUTE)
    elif kind=='results':
        text(d,(85,202),scene['title'],92,INK,True)
        text(d,(95,320),'MATCH / ORIGINAL PICK',25,MUTE,True)
        text(d,(1420,320),'FT',25,MUTE,True);text(d,(1600,320),'RESULT',25,MUTE,True)
        for i,p in enumerate(scene['rows']):
            y=380+i*125;win=p['settlement']=='FULL_WIN';d.rounded_rectangle((80,y,1840,y+110),radius=10,fill='#F5F3EC')
            text(d,(105,y+13),short(p['home'])+' v '+short(p['away']),38,INK,True,width=950)
            text(d,(105,y+63),pick_label(p)+('  / RESERVE' if p['tier']=='RESERVE' else '  / EXTRA' if p['tier']=='ADDITIONAL' else ''),27,MUTE)
            text(d,(1415,y+28),f"{p['ft'][0]}–{p['ft'][1]}",45,INK,True)
            pill(d,(1580,y+26,1805,y+81),'WIN' if win else 'LOSS',GREEN if win else RED,PAPER,33)
    elif kind=='match':
        p=scene['pick'];home,away=short(p['home']),short(p['away'])
        pill(d,(83,203,340,255),'PICK '+str(scene['number'])+' / 05',INK,PAPER)
        text(d,(1815,230),datetime.fromisoformat(p['kickoff']).astimezone(timezone.utc).strftime('%H:%M UTC'),38,INK,True,anchor='rm')
        pitch(d,(160,328,1760,780))
        shirt(d,525,485,home,1.15);shirt(d,1395,485,away,1.15)
        text(d,(960,530),'VS',70,MUTE,True,anchor='mm')
        text(d,(525,716),home,66,INK,True,700,'mm');text(d,(1395,716),away,66,INK,True,700,'mm')
        pill(d,(580,800,1340,874),pick_label(p),LIME,INK,52)
    elif kind=='choice':
        p=scene['pick'];text(d,(95,215),short(p['home'])+' v '+short(p['away']),65,PAPER,True,width=1700)
        text(d,(90,340),pick_label(p),166,LIME,True,width=1720)
        text(d,(97,560),scene['headline'],57,PAPER,True,width=1700)
        text(d,(97,665),scene['detail'],39,'#BAC5B9',False,width=1720)
        pill(d,(95,805,550,871),p['tier'], '#31443C',PAPER,27)
        text(d,(585,822),'Research lean • not a guaranteed outcome',30,'#BAC5B9')
    elif kind=='recap':
        text(d,(85,201),"TODAY'S FIVE LEANS",96,INK,True)
        for i,p in enumerate(scene['rows']):
            y=340+i*108;d.rounded_rectangle((80,y,1840,y+93),radius=7,fill='#F5F3EC')
            text(d,(105,y+25),datetime.fromisoformat(p['kickoff']).astimezone(timezone.utc).strftime('%H:%M'),36,INK,True)
            text(d,(265,y+27),short(p['home'])+' v '+short(p['away']),37,INK,True,width=850)
            pill(d,(1160,y+17,1808,y+77),pick_label(p),LIME,INK,34)
        # Date, UTC and scan time already appear in header/footer.
    elif kind=='end':
        text(d,(90,220),'KEEP THE RECEIPTS.',130,PAPER,True,width=1720)
        text(d,(95,440),'Five picks. No edits after kickoff.',65,LIME,True)
        text(d,(95,590),'Next episode: every final score.',54,PAPER)
        text(d,(95,752),'Which match would you leave alone?',47,'#BAC5B9')
        # Keep bottom caption area clear.
    im.save(path)

def make_scenes(data,recap):
    p=data['predictions'];result=[]
    def add(kind,speech,**kw):result.append(dict(kind=kind,speech=speech,**kw))
    add('hook',"Liverpool, City, and a three-and-a-half goal line in Eindhoven. Five football leans for Wednesday, November fourth. But first, yesterday's results. All of them.")
    add('record',"Yesterday was two wins and six losses, including the reserve and both extra selections. The handicap picks split two and two. All four totals lost. Here's the full card.",section='03 NOV / THE RECAP')
    add('results',"Oldham and Bolton: full wins, both one zero. Shakhtar: full loss, zero one. Derby: full loss, zero four.",section='03 NOV / ASIAN HANDICAP',title='AH: TWO WINS, TWO LOSSES',rows=[x for x in recap if x['market']=='AH'])
    add('results',"Watford beat Lincoln one zero. Queens Park Rangers and Burnley drew one one. Huddersfield and Luton also drew one one. All three over selections lost. Portsmouth won three one, so the reserve under lost too.",section='03 NOV / TOTAL GOALS',title='TOTALS: FOUR LOSSES',rows=[x for x in recap if x['market']=='OU'])
    speeches=[
      ("First, P S V against Club Brugge. Twenty hundred U T C. Under three and a half is the lead lean on today's card.","Three goals or fewer.","4+ goals = loss", "A two one finish works. A two two finish doesn't. The selection is under three and a half, not a call that either side fails to score."),
      ("Next, Leipzig against Manchester City, also at twenty hundred U T C. Another under three and a half, but a more cautious selection.","UNDER 3.5. CAUTIOUS.","0–3 total goals = win • 4+ = loss", "This one stays on the cautious list. Under three and a half needs no more than three goals in the match. Four goals, and the pick loses."),
      ("The early Champions League game: Fenerbahche against Liverpool at seventeen forty-five U T C. My handicap lean is Fenerbahche plus one and a quarter.","A narrow defeat still matters.","Draw or win: full win • lose by one: half win", "Fenerbahche can lose by one and this is still a half win. A draw or a home win pays in full. Liverpool winning by two or more beats the selection."),
      ("Over to Belgium. Kortrijk against Mechelen, nineteen thirty U T C. Mechelen plus a quarter goes on the secondary list.","MECHELEN +0.25", "Away win: full win • draw: half win • defeat: loss", "This is a lean toward the visitors with a little protection. Mechelen winning is a full win. A draw is a half win. A Kortrijk win means a loss."),
      ("And in the Championship: Bristol City against Wolves, twenty hundred U T C. Bristol City plus a quarter is the final secondary lean.","BRISTOL CITY +0.25", "Home win: full win • draw: half win • defeat: loss", "A Bristol City win pays in full. A draw returns a half win. If Wolves win, the pick loses. That's the exact line being recorded today.")]
    for i,(pick,words) in enumerate(zip(p,speeches),1):
        a,headline,detail,b=words
        add('match',a,section='04 NOV / '+('TOTAL GOALS' if pick['market']=='OU' else 'ASIAN HANDICAP'),pick=pick,number=i)
        add('choice',b,section='THE SELECTION / '+str(i).zfill(2),pick=pick,headline=headline,detail=detail)
    add('recap',"Here's the complete card in kickoff order. Fenerbahche plus one and a quarter. Mechelen plus a quarter. Under three and a half in P S V and in Leipzig. Bristol City plus a quarter. These are research leans, not guaranteed outcomes.",section='04 NOV / SAVE THE CARD',rows=sorted(p,key=lambda x:x['kickoff']))
    add('end',"The five selections are recorded before kickoff. Next time, we'll show every final score, including the losses. Which match would you leave alone? Leave your answer below.")
    return result

def soundtrack(path,duration):
    import numpy as np,wave
    sr=24000;t=np.arange(math.ceil(duration*sr))/sr
    # Original restrained sports pulse: synthesized oscillators, no samples.
    sound=np.zeros(len(t))
    for j,hz in enumerate([65.4064,98.0,130.8128]):sound+=.018*np.sin(2*np.pi*hz*t)*(.7+.3*np.sin(2*np.pi*.13*t+j))
    phase=t%(.625);sound+=.07*np.exp(-phase*24)*np.sin(2*np.pi*(50*phase+1.8*(1-np.exp(-phase*30))))
    phase2=(t+.3125)%.625;sound+=.008*np.sin(2*np.pi*4200*t)*np.exp(-phase2*90)
    sound*=np.minimum(t/2,1)*np.minimum((duration-t)/3,1)
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((sound*32767).astype('<i2').tobytes())

def render(episode,out,model,voices):
    episode=Path(episode);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    data=json.loads((episode/'daily.json').read_text());recap=json.loads((episode/'previous-chat-recap.json').read_text())['records']
    ledger=read_ledger(episode/'prediction-ledger.jsonl')
    validate_edition(data,recap,ledger)
    from .local_voice import LocalVoice
    narrator=LocalVoice(model,voices)
    scenes=make_scenes(data,recap);timeline=[];subs=[];elapsed=0
    (out/'script.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2))
    for i,s in enumerate(scenes):
        stem=f'scene-{i:02}';card(s,out/(stem+'.png'))
        captions=narrator.synthesize(s['speech'],out/(stem+'.wav'))
        duration=math.ceil((float(probe(out/(stem+'.wav'))['format']['duration'])+.35)*30)/30
        for cap in captions:
            subs.append(f"{len(subs)+1}\n{stamp(elapsed+cap['start'])} --> {stamp(elapsed+cap['end'])}\n"+cap['text']+'\n')
        # Moving scan marker + opening reveal + slight camera drift; no fake footage.
        vf="zoompan=z='min(zoom+0.000012,1.006)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30,fade=t=in:st=0:d=0.18,drawbox=x=0:y=0:w=iw:h=6:color=0xD7FA55:t=fill,format=yuv420p"
        run(['ffmpeg','-y','-v','error','-loop','1','-i',str(out/(stem+'.png')),'-i',str(out/(stem+'.wav')),'-t',str(duration),'-vf',vf,'-af','apad,loudnorm=I=-16:TP=-1.5:LRA=9','-c:v','libx264','-preset','ultrafast','-crf','20','-threads','2','-c:a','aac','-ar','48000','-ac','2',str(out/(stem+'.mp4'))])
        timeline.append(dict(start=round(elapsed,3),duration=duration,kind=s['kind'],speech=s['speech']));elapsed+=duration
        print(f'{i+1}/{len(scenes)} {s["kind"]}: {duration:.1f}s',flush=True)
    (out/'subtitles.srt').write_text('\n'.join(subs));(out/'timeline.json').write_text(json.dumps(timeline,indent=2))
    (out/'concat.txt').write_text(''.join(f"file 'scene-{i:02}.mp4'\n" for i in range(len(scenes))))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','concat.txt','-c','copy','joined.mp4'],cwd=out)
    soundtrack(out/'music.wav',elapsed)
    run(['ffmpeg','-y','-v','error','-i','joined.mp4','-i','music.wav','-filter_complex',"[0:a][1:a]amix=inputs=2:duration=first:weights='1 0.32'[a];[0:v]subtitles=subtitles.srt:force_style='FontName=Nimbus Sans,FontSize=16,MarginV=24,Outline=1,BackColour=&H90000000,BorderStyle=3'[v]",'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','19','-threads','2','-c:a','aac','-b:a','192k','-movflags','+faststart','video.mp4'],cwd=out)
    run(['ffmpeg','-v','error','-i',str(out/'video.mp4'),'-f','null','-'])
    info=probe(out/'video.mp4');v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'])==(1920,1080);assert abs(float(info['format']['duration'])-elapsed)<1
    # Purpose-designed thumbnail, not a reused opening frame.
    im=Image.new('RGB',(W,H),INK);d=ImageDraw.Draw(im)
    d.polygon([(1240,0),(1920,0),(1920,1080),(960,1080)],fill=LIME)
    text(d,(95,80),'04 NOV / FOOTBALL PICKS',45,LIME,True)
    text(d,(90,240),'BACK THE',150,PAPER,True);text(d,(90,405),'UNDERDOG?',150,PAPER,True)
    text(d,(98,625),'FENERBAHÇE +1.25',78,LIME,True)
    pill(d,(95,820,905,940),'PLUS TWO UNDER 3.5 LEANS',PAPER,INK,45)
    shirt(d,1520,410,'Fenerbahçe',2.1);text(d,(1505,810),'+1.25',158,INK,True,anchor='mm')
    im.resize((1280,720)).save(out/'thumbnail.jpg',quality=94);im.save(out/'thumbnail.png')
    chapters=[]
    for idx,title in [(0,'Today’s card'),(1,'Yesterday: every result'),(4,'PSV vs Club Brugge'),(6,'Leipzig vs Man City'),(8,'Fenerbahce vs Liverpool'),(10,'Kortrijk vs Mechelen'),(12,'Bristol City vs Wolves'),(14,'Full picks recap')]:
        seconds=int(timeline[idx]['start']);chapters.append(f'{seconds//60:02}:{seconds%60:02} {title}')
    description="Football predictions for 4 November 2026. All kickoff times are UTC.\n\n"+'\n'.join(chapters)+"\n\nTODAY’S RECORDED LEANS\n"+'\n'.join(datetime.fromisoformat(p['kickoff']).astimezone(timezone.utc).strftime('%H:%M UTC')+' — '+short(p['home'])+' vs '+short(p['away'])+': '+pick_label(p)+' ['+p['tier']+']' for p in sorted(data['predictions'],key=lambda x:x['kickoff']))+"\n\nYesterday’s retrieved chat selections: 2 full wins, 6 full losses, including one reserve and two additional picks. AH: 2/4; totals: 0/4. This is a reconstructed chat recap, not a long-term audited record. The new pre-match ledger begins with today’s five picks.\n\nLines are from the 08:00 UTC scan (15:00 Bangkok). Historical group statistics are descriptive, not calibrated match probabilities or validated betting edges. No guaranteed outcomes. No bookmaker links.\n\nOriginal graphics and original synthesized background music. AI-assisted English narration. Club-colour illustrations are original graphics, not official crests.\n\nFixture verification: https://www.uefa.com/uefachampionsleague/\nSource data: https://github.com/meepo1150-code/football-odds-scanner\n"
    meta=dict(title='Fenerbahce +1.25? PSV & Man City Under 3.5 | Football Picks 4 Nov 2026',description=description,tags=['football predictions','Champions League','Fenerbahce Liverpool','PSV Club Brugge','Leipzig Manchester City'],defaultLanguage='en',privacyStatus='private')
    (out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));(out/'description.txt').write_text(description)
    (out/'MUSIC_LICENSE.txt').write_text('Original procedural music and graphic illustrations created for this episode. No third-party music samples or match footage. Rights to these original assets granted for use in this project.\n')
    for name in ('daily.json','previous-chat-recap.json','prediction-ledger.jsonl','evidence.json'):(out/name).write_bytes((episode/name).read_bytes())
    manifest=dict(video_created=True,audio_created=True,qa_decode_passed=True,width=1920,height=1080,duration=float(info['format']['duration']),predictions=5,recap_records=8,display_timezone='UTC',voice='Kokoro bm_george OFFLINE',ledger_head=ledger[-1]['hash'],youtube_uploaded=False,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True);p.add_argument('--output',required=True);p.add_argument('--model',required=True);p.add_argument('--voices',required=True);a=p.parse_args();render(a.episode,a.output,a.model,a.voices)
