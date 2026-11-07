"""Data-driven sports broadcast, original shirts, measured narration and stage motion."""
import argparse,json,math,subprocess,textwrap,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
from .engine import read_ledger,label
from .local_voice import LocalVoice
from .broadcast import soundtrack,pitch
from .daily_v2 import probe,stamp
NAVY='#081B31';MINT='#63F5CA';WHITE='#F4F8FF';MUTED='#A0B4CA';BLUE='#173650';RED='#FF7E80'
FONT='/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf';BOLD='/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf'
ALIASES={'FC Vysocina Jihlava':'Jihlava','MFK Karvina':'Karvina','Vejle BK':'Vejle','FC Fredericia':'Fredericia','Willem II Tilburg':'Willem II','PEC Zwolle':'PEC Zwolle','Bristol Rovers':'Bristol Rovers','Cambridge United':'Cambridge United','Lillestroem SK':'Lillestrom','FC Viktoria Plzen':'Viktoria Plzen','AS Monaco':'Monaco','FC Nordsjaelland':'Nordsjaelland','SC Freiburg':'Freiburg'}
COLORS={'FC Vysocina Jihlava':('#EFC13C','#2E6FCA'),'MFK Karvina':('#3BB67F','#FFFFFF'),'Vejle BK':('#CC344B','#FFFFFF'),'FC Fredericia':('#F0F3F8','#C8374B'),'Willem II Tilburg':('#C83349','#3F6CCA'),'PEC Zwolle':('#3D85D9','#FFFFFF'),'Bristol Rovers':('#3082D6','#F5F6FF'),'Cambridge United':('#E8B83E','#171D24')}
def run(cmd):subprocess.run([str(x) for x in cmd],check=True)
def short(n):return ALIASES.get(n,n)
def names(p):return short(p['home'])+' v '+short(p['away'])
def pick(p):
 return (short(p['home'] if p['selection']=='HOME' else p['away'])+f" {p['line']:+g} AH") if p['market']=='AH' else f"{p['selection'].title()} {p['line']:g} goals"
def spoken(p):return short(p['home'])+' draw no bet' if p['market']=='AH' and p['line']==0 else ('under three goals' if p['market']=='OU' and p['line']==3 else pick(p))
def dt(p):return datetime.fromisoformat(p['kickoff']).astimezone(timezone.utc)
def utc(p):return dt(p).strftime('%d %b %Y / %H:%M UTC').upper()
def text(dr,pos,v,size=46,fill=WHITE,bold=False,width=None):
 while True:
  f=ImageFont.truetype(BOLD if bold else FONT,size)
  if not width or dr.textbbox((0,0),str(v),font=f)[2]<=width:break
  size-=1
  if size<22:raise ValueError('Text overflow: '+str(v))
 dr.text(pos,str(v),font=f,fill=fill)
def scene(kind,title,speech,**kw):return dict(kind=kind,title=title,speech=speech,**kw)
def metric(p):
 e=p['evidence']
 if p['market']=='AH':return e['price_weighted_wr'],e['section_1_price']['n'],'S1 / PRICE BAND WEIGHTED WR'
 return e['ou_under_weighted_wr'],e['section_2_ou']['n'],'S2 / TOTALS WEIGHTED WR'

def shirt_image(team,path):
 im=Image.new('RGBA',(400,440));dr=ImageDraw.Draw(im);c,a=COLORS.get(team,('#437FC1','#FFFFFF'))
 pts=[(119,65),(60,102),(22,175),(90,212),(112,174),(112,396),(288,396),(288,174),(310,212),(378,175),(340,102),(281,65),(245,85),(155,85)]
 dr.polygon([(x+6,y+11) for x,y in pts],fill=(0,0,0,85));dr.polygon(pts,fill=c)
 dr.line([(119,65),(155,85),(200,119),(245,85),(281,65)],fill=a,width=14)
 dr.line([(26,174),(88,205)],fill=a,width=13);dr.line([(312,205),(374,174)],fill=a,width=13)
 dr.line([(114,392),(286,392)],fill=a,width=7);dr.line([(122,194),(122,378)],fill=(255,255,255,35),width=5)
 im.save(path)

def art(s,path,vertical=False):
 w,h=(1080,1920) if vertical else (1920,1080);im=Image.new('RGBA',(w,h));dr=ImageDraw.Draw(im);m=80
 title_y=260 if vertical else 180
 text(dr,(m,title_y),s['title'],46 if vertical else 56,MINT,True,w-2*m)
 p=s.get('p');kind=s['kind']
 if p:
  if vertical:
   text(dr,(m,385),short(p['home']),61,WHITE,True,900);text(dr,(m,465),'VS',32,MINT,True);text(dr,(m,520),short(p['away']),61,WHITE,True,900)
   text(dr,(m,650),utc(p),32,MUTED,False,900)
   y=1130
  else:
   text(dr,(m,270),names(p),72,WHITE,True,1740);text(dr,(m,365),utc(p)+' / '+p.get('league',''),29,MUTED,False,1740);y=485
  if kind=='evidence':
   text(dr,(m,y),f"{s['rate']:.2f}%",112 if vertical else 124,MINT,True)
   text(dr,(m,y+130),f"SETTLEMENT-WEIGHTED WR / N={s['n']}",32,WHITE,True,w-2*m)
   bx=m;by=y+192;bw=w-2*m;dr.rounded_rectangle((bx,by,bx+bw,by+22),radius=8,fill=BLUE)
   dr.rounded_rectangle((bx,by,bx+bw*s['rate']/100,by+22),radius=8,fill=MINT)
   text(dr,(bx,by+25),'0%',22,MUTED);text(dr,(bx+bw-55,by+25),'100%',22,MUTED)
   for j,l in enumerate(s.get('lines',[]) if not vertical else []):text(dr,(m,by+80+j*43),l,30,WHITE,False,w-2*m)
  elif kind=='pick':
   right=w-m if vertical else 1110
   dr.rounded_rectangle((m,y,right,y+110),radius=18,fill=MINT);text(dr,(m+22,y+20),pick(p),64 if vertical else 72,NAVY,True,right-m-44)
   for j,l in enumerate(s.get('lines',[])):text(dr,(m,y+145+j*50),l,30,MUTED,True,w-2*m)
  elif kind=='limitation':
   for j,l in enumerate(s['lines']):text(dr,(m,y+j*80),l,43,WHITE,True,w-2*m)
  elif kind=='result':
   for j,l in enumerate(s['lines']):text(dr,(m,y+j*112),l,53,(RED if p.get('settlement')=='FULL_LOSS' else MINT) if j else WHITE,True,w-2*m)
  elif vertical and kind=='end':text(dr,(m,y),'EVERY PICK. EVERY RESULT.',50,MINT,True,900)
 else:
  y=400
  for j,l in enumerate(s.get('lines',[])):
   text(dr,(m,y+j*90),l,42 if kind!='recap' else 35,WHITE,True,w-2*m)
 im.save(path)

def background(path,vertical=False):
 w,h=(1080,1920) if vertical else (1920,1080);im=Image.new('RGB',(w,h),NAVY);dr=ImageDraw.Draw(im)
 for y in range(h):
  a=y/h;dr.line((0,y,w,y),fill=(8+int(4*a),27+int(12*a),49+int(11*a)))
 pitch(dr,(w//2,260 if not vertical else 740,w-45,850 if not vertical else 1100),'#1C3D55')
 for x in range(0,w,150):dr.line((x,0,x-300,h),fill='#0E2941',width=1)
 dr.rectangle((0,0,w,16),fill=MINT)
 text(dr,(80,60 if not vertical else 120),'MATCHLEDGER FOOTBALL',38 if not vertical else 42,MINT,True,w-160)
 text(dr,(80,112 if not vertical else 182),'Every Pick. Every Result.',27,WHITE)
 dr.line((80,160 if not vertical else 235,w-80,160 if not vertical else 235),fill='#31536C',width=2)
 if not vertical:text(dr,(80,h-54),'RESEARCH ONLY / NO GUARANTEED OUTCOMES',22,MUTED,True,w-160)
 im.save(path)

def render_scene(s,i,work,voice,vertical=False):
 wav=work/f'{i:02}.wav';png=work/f'{i:02}-panel.png';out=work/f'{i:02}.mp4';art(s,png,vertical)
 caps=voice.synthesize(s['speech'],wav);duration=math.ceil((float(probe(wav)['format']['duration'])+.16)*24)/24
 w,h=(1080,1920) if vertical else (1920,1080)
 inputs=['-loop','1','-framerate','24','-i',work/'background.png','-loop','1','-framerate','24','-i',png]
 filters=["[0:v][1:v]overlay=x='-60*max(0,1-t/0.35)':y=0:shortest=1[v1]"];last='v1';audioidx=2
 p=s.get('p')
 if p and (s['kind'] in ['matchup','pick','end'] or vertical):
  for j,team in enumerate([p['home'],p['away']]):
   sh=work/f'{i:02}-shirt-{j}.png';shirt_image(team,sh);inputs+=['-loop','1','-framerate','24','-i',sh]
   scale=.68 if vertical else .62;cx=(160 if j==0 else 650) if vertical else (1235 if j==0 else 1530);cy=725 if vertical else 470
   filters.append(f'[{2+j}:v]scale={int(400*scale)}:{int(440*scale)}[shirt{j}]')
   filters.append(f"[{last}][shirt{j}]overlay=x='{cx}+{(-100 if j==0 else 100)}*max(0,1-t/0.5)+3*sin(t*1.3+{j})':y='{cy}+3*sin(t*1.1+{j})':shortest=1[v{2+j}]");last=f'v{2+j}'
  audioidx=4
 inputs+=['-i',wav]
 filters.append(f'[{last}]fade=t=in:d=0.12,format=yuv420p[v]')
 run(['ffmpeg','-y','-v','error',*inputs,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[v]','-map',f'{audioidx}:a','-t',duration,'-af','apad,loudnorm=I=-16:TP=-1.5:LRA=9','-c:v','libx264','-preset','ultrafast','-crf','22','-r','24','-threads','2','-c:a','aac','-ar','48000','-ac','2',out])
 return out,duration,caps

def render(ss,out,stem,voice,vertical=False):
 work=out/(stem+'-work');work.mkdir(exist_ok=True);background(work/'background.png',vertical)
 elapsed=0;parts=[];subs=[];timeline=[]
 for i,s in enumerate(ss):
  p,d,caps=render_scene(s,i,work,voice,vertical);parts.append(p)
  timeline.append(dict(start=round(elapsed,3),duration=d,title=s['title'],kind=s['kind'],prediction_id=s.get('p',{}).get('id'),speech=s['speech']))
  for c in caps:
   words=c['text'].replace('\n',' ').split();chunks=[];line='';width=34 if vertical else 64
   for word in words:
    if len(line+' '+word)>width:chunks.append(line);line=word
    else:line=(line+' '+word).strip()
   if line:chunks.append(line)
   groups=['\n'.join(chunks[j:j+2]) for j in range(0,len(chunks),2)];cursor=c['start'];total=sum(len(g) for g in groups)
   for g in groups:
    end=cursor+(c['end']-c['start'])*len(g)/total;subs.append((elapsed+cursor,elapsed+end,g));cursor=end
  elapsed+=d;print(stem,i,round(d,2),flush=True)
 if vertical and not 15<=elapsed<=20:raise ValueError(f'Short duration {elapsed} outside target')
 srt=out/(stem+'.srt');srt.write_text('\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{g}\n' for i,(a,b,g) in enumerate(subs)))
 listing=work/'concat.txt';listing.write_text('\n'.join("file '"+str(p.resolve())+"'" for p in parts));joined=work/'joined.mp4';run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
 music=work/'music.wav';soundtrack(music,elapsed)
 style=f"FontName=DejaVu Sans,FontSize={9 if vertical else 12},PrimaryColour=&H00FFFFFF,OutlineColour=&H00311B08,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV={54 if vertical else 20},MarginL=24,MarginR=24"
 final=out/(stem+'.mp4');run(['ffmpeg','-y','-v','error','-i',joined,'-i',music,'-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.10[a]','-map','0:v','-map','[a]','-vf',f"subtitles='{srt.resolve()}':force_style='{style}'",'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',final])
 info=probe(final);run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-'])
 (out/(stem+'-timeline.json')).write_text(json.dumps(timeline,indent=2));(out/(stem+'-script.json')).write_text(json.dumps(ss,indent=2))
 return dict(file=final.name,duration=float(info['format']['duration']),width=1080 if vertical else 1920,height=1920 if vertical else 1080,video_codec='h264',audio_codec='aac',decode='PASS',timeline=timeline,subtitle=srt.name)

def cover(s,path,vertical=False):
 temp=path.parent/(path.stem+'-temp');temp.mkdir(exist_ok=True);background(temp/'b.png',vertical);art(s,temp/'p.png',vertical);im=Image.open(temp/'b.png').convert('RGBA');im.alpha_composite(Image.open(temp/'p.png'))
 if s.get('p'):
  p=s['p']
  for j,t in enumerate([p['home'],p['away']]):
   shirt_image(t,temp/f's{j}.png');sh=Image.open(temp/f's{j}.png').resize((272,299) if vertical else (248,272));im.alpha_composite(sh,((160 if j==0 else 650) if vertical else (1235 if j==0 else 1530),725 if vertical else 470))
 if not vertical:im=im.resize((1280,720))
 im.convert('RGB').save(path);shutil.rmtree(temp)

def load_story(ep,d):
 story=json.loads((ep/'reviewed-storyboard.json').read_text());assert story['date']==d['date']
 byid={p['id']:p for p in d['predictions']}
 for s in story['full']+sum([x['scenes'] for x in story['shorts']],[]):
  if s.get('prediction_id'):s['p']=byid[s['prediction_id']]
 return story

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--episode',required=True);ap.add_argument('--output',required=True);ap.add_argument('--model',required=True);ap.add_argument('--voices',required=True);a=ap.parse_args();ep=Path(a.episode);out=Path(a.output).resolve();out.mkdir(exist_ok=True)
 d=json.loads((ep/'daily.json').read_text());r=json.loads((ep/'ft-settlement-report.json').read_text());rows=read_ledger(ep/'prediction-ledger.jsonl');assert len(rows)==len(d['predictions'])
 for p in d['predictions']:
  row=next(x for x in rows if x['prediction']['id']==p['id']);assert all(row['prediction'][k]==p[k] for k in row['prediction']);assert datetime.fromisoformat(row['recorded_at'])<datetime.fromisoformat(p['kickoff'])
 story=load_story(ep,d)
 voice=LocalVoice(a.model,a.voices);ss=story['full'];stem='matchledger-full-'+d['date'];qa=[]
 q=render(ss,out,stem,voice);qa.append(q)
 # Chapters use actual rendered boundaries. Keep all match stages in the video.
 chapter_rows=[x for x in q['timeline'] if x['kind'] in ['hook','record','matchup','recap','end'] or (x['kind']=='result' and x==next(t for t in q['timeline'] if t['kind']=='result'))]
 chapters='\n'.join(f"{int(x['start'])//60:02}:{int(x['start'])%60:02} "+(names(next(p for p in d['predictions'] if p['id']==x['prediction_id'])) if x['kind']=='matchup' else x['title']) for x in chapter_rows)
 edition=datetime.fromisoformat(d['date']).strftime('%d %b %Y')
 title=f"Football Predictions {edition} | "+' / '.join(short(p['home']) for p in d['predictions'])
 card='\n'.join(f"{names(p)} | {utc(p)} | {pick(p)}" for p in d['predictions'])
 def wr(v):return 'N/A' if v is None else f'{v*100:.2f}%'
 desc=f"{len(d['predictions'])} cautious editorial research leans from the recorded 08:00 UTC scan.\n\n"+card+"\n\nYesterday, every verified pick:\n"+'\n'.join(f"{names(p)} | {pick(p)} | FT {p['ft']} | {p['settlement']}" for p in r['details'])
 desc+='\nDaily settlement-weighted WR: '+', '.join(f"{m} {wr(r['daily'][m]['wr'])}" for m in ['AH','OU'])
 desc+='\nCumulative verified ledger WR: '+', '.join(f"{m} {wr(r['cumulative'][m]['wr'])}" for m in ['AH','OU'])
 dq=json.loads((ep/'data-qa.json').read_text())
 desc+='\n\n'+chapters+f"\n\nScan Health {dq['scan_health']}. Slot receipt: {dq['strict_snapshots']} strict snapshots / {dq['cohort_fixtures']} response fixtures; discovery health: {dq['health_discovery_fixtures']} fixtures / {dq['health_valid_core_odds']} core-valid AH odds. These are different populations. "
 desc+="Statistical report predates scan. Groups overlap and are pooled across leagues. Historical WR is not match probability or ROI. No validated edge or guaranteed outcomes. "+dq['historical_scope']+'. '+dq['prior_chat_coverage']
 desc+='\nCumulative N: '+', '.join(f"{m} N={sum(r['cumulative'][m]['counts'].values())}" for m in ['AH','OU'])
 desc+="\nMatchLedger Football. Every Pick. Every Result. All kickoff dates and times UTC."


 meta=[dict(file=stem+'.mp4',title=title,description=desc,hashtags='#FootballPredictions #MatchLedgerFootball #FootballStats',tags=['football predictions',edition,'Asian handicap','football stats','MatchLedger Football']+[short(p['home']) for p in d['predictions']],chapters=chapters)]
 cover(scene('hook',f"{len(d['predictions'])} CAUTIOUS LEANS",'',lines=[edition.upper(),' / '.join(short(p['home']) for p in d['predictions'][:2]),'EVERY RESULT / ALL KICKOFFS UTC']),out/('matchledger-thumbnail-'+d['date']+'.png'))
 selected=[next(p for p in d['predictions'] if p['id']==x['prediction_id']) for x in story['shorts'][:3]]

 for i,p in enumerate(selected,1):
  st=f'matchledger-short-{i:02}-'+d['date'];qs=next(x['scenes'] for x in story['shorts'] if x['prediction_id']==p['id']);qa.append(render(qs,out,st,voice,True));cover(scene('pick','THE STATISTICAL CASE','',p=p,lines=[f'WEIGHTED WR {metric(p)[0]:.2f}% / N={metric(p)[1]}','CAUTIOUS RESEARCH LEAN']),out/(st+'-cover.png'),True)
  v,n,_=metric(p);meta.append(dict(file=st+'.mp4',title=f'{names(p)}: Why {pick(p)}? | {edition} #Shorts',description=f"Kickoff: {utc(p)}. Pick: {pick(p)}. Historical settlement-weighted WR {v:.2f}% across {n} records in the matching {'handicap price' if p['market']=='AH' else 'total line/price'} cohort. Cautious editorial research lean, also in the full MatchLedger Football episode for {edition}. Groups overlap and are pooled across leagues; historical WR is not this match's probability. No validated edge or guaranteed result. "+('The other Under 3.0 fixture shares this structure.' if p['market']=='OU' else ''),hashtags='#Shorts #FootballPredictions #MatchLedgerFootball',tags=['football predictions',short(p['home']),short(p['away']),'football stats','Shorts']))
 for m in meta:(out/(Path(m['file']).stem+'-metadata.txt')).write_text('TITLE\n'+m['title']+'\n\nDESCRIPTION\n'+m['description']+'\n\nHASHTAGS\n'+m['hashtags']+'\n\nTAGS\n'+', '.join(m['tags']))
 (out/'youtube-metadata.json').write_text(json.dumps(meta,indent=2));(out/'media-qa.json').write_text(json.dumps(qa,indent=2))
 for f in ep.iterdir():
  if f.is_file() and not f.name.endswith('.lock'):shutil.copy2(f,out/f.name)
 (out/'audio-license.txt').write_text('Local Kokoro ONNX bm_george English narration, Apache 2.0 model. Original procedural music with no third-party samples. Original generic color-only shirts: no club crests, maker marks, sponsors or copied kit patterns. Model source: thewh1teagle/kokoro-onnx model-files-v1.0.')
 print('RENDER_COMPLETE',flush=True)
if __name__=='__main__':main()
