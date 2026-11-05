"""Render a reviewed edition. No football/provider network calls or production writes."""
import argparse,json,math,subprocess,textwrap,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
from .engine import read_ledger,label
from .local_voice import LocalVoice
from .broadcast import soundtrack,shirt,pitch
INK='#14201E';PAPER='#E8E6DF';LIME='#D7FA55';GREEN='#21745C';RED='#E96850'
FONT='/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf';BOLD='/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf'
def run(a):subprocess.run([str(x) for x in a],check=True)
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def stamp(t):
 n=round(t*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'
def txt(d,xy,v,size=50,color=PAPER,bold=False,width=None):
 while True:
  f=ImageFont.truetype(BOLD if bold else FONT,size)
  if not width or d.textbbox((0,0),v,font=f)[2]<=width:break
  size-=1
  if size<22:raise ValueError('Text overflow '+v)
 d.text(xy,v,font=f,fill=color)
def number(v):return f'{v:.2f}'.rstrip('0').rstrip('.')
def names(p):return p['home']+' v '+p['away']
def scene(title,speech,lines=None,pick=None,stat=None):return dict(title=title,speech=speech,lines=lines or [],pick=pick,stat=stat)
def scenes(d,r):
 ps=d['predictions'];ah=r['daily']['AH'];ou=r['daily']['OU'];out=[]
 out.append(scene('THE RECORD COMES FIRST',f"Three careful handicap leans for November fifth, and every result from yesterday. Plzen, Trabzonspor, and Monaco make today's card. We reviewed thirty five priced fixtures from the fifteen hundred Bangkok scan. These are editorial research leans, not validated betting edges. Welcome to MatchLedger Football. Every pick. Every result.",['05 NOV 2026','3 EDITORIAL LEANS','35 PRICED FIXTURES REVIEWED']))
 for market in ['AH','OU']:
  rows=[x for x in r['details'] if x['market']==market];lines=[f"{names(p)} | {label(p)} | {p['ft'][0]}-{p['ft'][1]} | {p['settlement'].replace('_',' ')}" for p in rows]
  speech="Yesterday's handicap card: Fenerbahce plus one and a quarter won, with a three two home victory over Liverpool. Mechelen plus a quarter also won, beating Kortrijk three one. Bristol City plus a quarter lost, one two against Wolves. All three original selections are included." if market=='AH' else "On totals, P S V against Club Brugge finished one two. Under three and a half won. Leipzig against Manchester City finished two three, so under three and a half lost. We keep both results on the record. There were no pending selections in the five pick archive."
  out.append(scene('04 NOV / '+market+' RESULTS',speech,lines))
 out.append(scene('WEIGHTED WR / VERIFIED LEDGER',"The settlement weighted handicap win rate was sixty six point six seven percent, from two full wins and one full loss. Totals were fifty percent, from one full win and one full loss. Cumulative rates are the same because November fourth is the only verified ledger episode located. The five archived selections have complete result coverage. Earlier reconstructed chat results are excluded from these cumulative figures.",['AH 66.67% | 2 FULL WINS / 1 FULL LOSS','OU 50.00% | 1 FULL WIN / 1 FULL LOSS','DAILY = CUMULATIVE | VERIFIED HISTORY: 1 DAY','FT COVERAGE 5/5 | PENDING 0']))
 for i,p in enumerate(ps):
  e=p['evidence'];b=e['section_1_line'];price=e['section_1_price'];c=e['section_3_4_context'];bw=e['baseline_weighted_wr'];pw=e['price_weighted_wr'];cn=c['ah_n'];cw=c['ah_favorite_win_pct']
  if i==0:speech=f"First, Lillestrom against Viktoria Plzen, at seventeen forty five U T C on November fifth. Our lean is Plzen minus a quarter. Comparable away favorites on this handicap recorded a settlement weighted win rate of {bw} percent across {b['n']} matches. The matching price band reached {pw} percent across {price['n']}. The three goal context was positive in {cw} percent of {cn} records. Those groups overlap, and the context sample is small, so confidence stays cautious."
  elif i==1:speech=f"Next, Trabzonspor against Freiburg, also seventeen forty five U T C. The lean is Trabzonspor at level handicap, or draw no bet. The home level line group recorded {bw} percent weighted wins across {b['n']} matches. The relevant price band recorded {pw} percent across {price['n']}. In the three goal context, positive handicap returns occurred in {cw} percent of just {cn} records. That small context group limits the case. This remains a cautious research lean."
  else:speech=f"Finally, Monaco against Nordsjaelland at twenty hundred U T C. Monaco minus one and a quarter is our third lean. The handicap line group recorded {bw} percent weighted wins across {b['n']} matches. Its matching price band recorded {pw} percent across {price['n']}. With a three and a quarter goal line, positive handicap returns occurred in {cw} percent of {cn} records. The direction agrees across groups, but league specific strength is unproven. We keep the classification cautious."
  out.append(scene('TODAY / '+str(i+1)+' OF '+str(len(ps)),speech,pick=p,stat=[f'LINE WEIGHTED WR {bw:.2f}% / N={b["n"]}',f'PRICE BAND WEIGHTED WR {pw:.2f}% / N={price["n"]}',f'CONTEXT POSITIVE RETURN {cw:.2f}% / N={cn}']))
 out.append(scene('SAVE THE COMPLETE CARD',"The complete card: Plzen minus a quarter, Trabzonspor draw no bet, and Monaco minus one and a quarter. We found no totals selection with enough agreement between the chosen historical groups. Historical win rates describe these records; they are not today's match probabilities. Overlapping groups are not independent confirmations. Tomorrow, the same ledger keeps every final result, including losses. MatchLedger Football. Every pick. Every result.",[f"{datetime.fromisoformat(p['kickoff']).strftime('%H:%M')} UTC | {label(p)}" for p in ps]+['EDITORIAL RESEARCH LEANS / ALL TIMES UTC']))
 return out

def graphic(s,path,vertical=False):
 w,h=(1080,1920) if vertical else (1920,1080);im=Image.new('RGB',(w,h),INK);dr=ImageDraw.Draw(im)
 margin=85
 if not vertical:pitch(dr,(1040,350,1820,830),color='#20332C')
 txt(dr,(margin,80 if vertical else 38),'MATCHLEDGER FOOTBALL',42 if vertical else 34,LIME,True,width=w-170)
 txt(dr,(margin,140 if vertical else 86),'Every Pick. Every Result.',27,PAPER,width=w-170)
 dr.line((margin,200 if vertical else 140,w-margin,200 if vertical else 140),fill=GREEN,width=3)
 txt(dr,(margin,235 if vertical else 173),'05 NOV 2026 / ALL TIMES UTC',28,LIME,True)
 txt(dr,(margin,305 if vertical else 225),s['title'],46 if vertical else 62,PAPER,True,width=w-170)
 p=s.get('pick')
 if p:
  if vertical:
   txt(dr,(margin,460),p['home'],68,PAPER,True,width=860);txt(dr,(margin,550),'VS',45,GREEN,True);txt(dr,(margin,625),p['away'],68,PAPER,True,width=860)
   txt(dr,(margin,780),datetime.fromisoformat(p['kickoff']).strftime('%d NOV %H:%M UTC'),38,LIME)
   dr.rounded_rectangle((70,890,970,1080),radius=18,fill=LIME);txt(dr,(95,930),label(p),68,INK,True,width=850)
   for i,v in enumerate((s.get('stat') or [])[:2]):txt(dr,(margin,1160+i*90),v,39,PAPER,True,width=850)
   txt(dr,(margin,1370),'CAUTIOUS RESEARCH LEAN',31,LIME,True)
  else:
   txt(dr,(margin,343),p['home'],77,PAPER,True,width=1690);txt(dr,(margin,440),'v '+p['away'],77,PAPER,True,width=1690)
   txt(dr,(margin,540),datetime.fromisoformat(p['kickoff']).strftime('%d NOV %H:%M UTC')+' / '+p['league'],32,LIME,width=1700)
   dr.rounded_rectangle((80,600,1840,700),radius=14,fill=LIME);txt(dr,(110,615),label(p),64,INK,True,width=1650)
   for i,v in enumerate(s.get('stat') or []):txt(dr,(margin,730+i*46),v,33,PAPER,True,width=1700)
 else:
  y=365
  for line in s['lines']:
   for sub in textwrap.wrap(line,width=90):txt(dr,(margin,y),sub,39,PAPER,True,width=1720);y+=60
   y+=30
  if y>870:raise ValueError('Content invades caption area')
 txt(dr,(margin,h-(90 if vertical else 190)),'RESEARCH ONLY / NO GUARANTEED OUTCOMES',24,GREEN,True,width=w-170)
 im.save(path)

def render_video(ss,out,stem,voice,vertical=False):
 temp=out/(stem+'-work');temp.mkdir();w,h=(1080,1920) if vertical else (1920,1080);elapsed=0;subs=[];timeline=[];parts=[]
 for i,s in enumerate(ss):
  png=temp/f'{i}.png';wav=temp/f'{i}.wav';mp4=temp/f'{i}.mp4';graphic(s,png,vertical)
  caps=voice.synthesize(s['speech'],wav);duration=math.ceil((float(probe(wav)['format']['duration'])+.2)*30)/30
  if vertical:
   if duration>20:raise ValueError(f'Short too long {duration}')
   duration=max(15,duration)
  for c in caps:
   words=c['text'].replace('\n',' ').split();chunks=[];line=''
   for word in words:
    if len(line+' '+word)>(32 if vertical else 66):chunks.append(line);line=word
    else:line=(line+' '+word).strip()
   if line:chunks.append(line)
   groups=['\n'.join(chunks[j:j+2]) for j in range(0,len(chunks),2)];total=sum(len(v) for v in groups);cursor=c['start']
   for group in groups:
    end=cursor+(c['end']-c['start'])*len(group)/total;subs.append((elapsed+cursor,elapsed+end,group));cursor=end
  vf=f"zoompan=z='1.003+0.002*sin(on/60)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps=30,fade=t=in:d=0.2,drawtext=fontfile={FONT}:text='MATCHLEDGER / EVERY PICK. EVERY RESULT.':fontsize=24:fontcolor=0xD7FA55:x='w-mod(t*90,w+tw)':y=h-40,format=yuv420p"
  run(['ffmpeg','-y','-v','error','-loop','1','-i',png,'-i',wav,'-t',duration,'-vf',vf,'-af','apad,loudnorm=I=-16:TP=-1.5:LRA=9','-c:v','libx264','-preset','ultrafast','-crf','24','-threads','2','-c:a','aac','-ac','2','-ar','48000',mp4]);parts.append(mp4);timeline.append(dict(start=round(elapsed,3),duration=duration,title=s['title'],speech=s['speech']));elapsed+=duration
  print(stem,i,round(duration,2),flush=True)
 srt=out/(stem+'.srt');srt.write_text('\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{v}\n' for i,(a,b,v) in enumerate(subs)))
 listing=temp/'concat.txt';listing.write_text('\n'.join("file '"+str(x.resolve())+"'" for x in parts));joined=temp/'joined.mp4';run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
 music=temp/'music.wav';soundtrack(music,elapsed)
 style=f"FontName=DejaVu Sans,FontSize={8 if vertical else 12},PrimaryColour=&H00FFFFFF,OutlineColour=&H0014201E,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV={44 if vertical else 16},MarginL={18 if vertical else 32},MarginR={18 if vertical else 32}"
 final=out/(stem+'.mp4');run(['ffmpeg','-y','-v','error','-i',joined,'-i',music,'-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.15[a]','-map','0:v','-map','[a]','-vf',f"subtitles='{srt.resolve()}':force_style='{style}'",'-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',final])
 run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-']);info=probe(final);v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio');assert (v['width'],v['height'],v['codec_name'],a['codec_name'])==(w,h,'h264','aac')
 (out/(stem+'-timeline.json')).write_text(json.dumps(timeline,indent=2));shutil.rmtree(temp)
 return dict(file=final.name,duration=float(info['format']['duration']),width=w,height=h,video_codec=v['codec_name'],audio_codec=a['codec_name'],decode='PASS',subtitle=srt.name,timeline=timeline)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--episode');ap.add_argument('--output');ap.add_argument('--model');ap.add_argument('--voices');args=ap.parse_args();ep=Path(args.episode);out=Path(args.output);out.mkdir()
 d=json.loads((ep/'daily.json').read_text());r=json.loads((ep/'ft-settlement-report.json').read_text());ledger=read_ledger(ep/'prediction-ledger.jsonl');assert len(ledger)==len(d['predictions'])
 for p in d['predictions']:
  row=next(x for x in ledger if x['prediction']['id']==p['id']);assert all(row['prediction'][k]==p[k] for k in row['prediction']);assert datetime.fromisoformat(row['recorded_at'])<datetime.fromisoformat(p['kickoff']);assert datetime.fromisoformat(d['statistics_generated_at'])<datetime.fromisoformat(row['recorded_at'])
 voice=LocalVoice(args.model,args.voices);ss=scenes(d,r);qa=[render_video(ss,out,'matchledger-full-2026-11-05',voice)];meta=[]
 chapters='\n'.join(f"{int(x['start'])//60:02}:{int(x['start'])%60:02} {x['title']}" for x in qa[0]['timeline'])
 title='Football Predictions 5 Nov 2026 | Monaco, Plzen & Trabzonspor | Every Result'
 desc="Today's cautious AH research leans: Viktoria Plzen -0.25 (17:45 UTC), Trabzonspor 0 (17:45 UTC), Monaco -1.25 (20:00 UTC). All kickoffs 5 November 2026 UTC.\n\nYesterday: Fenerbahce 3-2 Liverpool (win), Kortrijk 1-3 Mechelen (win), Bristol City 1-2 Wolves (loss), PSV 1-2 Club Brugge (under win), Leipzig 2-3 Man City (under loss). Verified daily and cumulative weighted WR: AH 66.67% (N=3), OU 50% (N=2). Only one archived prediction day; no pending.\n\n"+chapters+"\n\nMatchLedger Football. Every Pick. Every Result.\nHistorical rates are descriptive, not match probabilities. Editorial research only; no validated edge or guaranteed outcome. Gambling involves financial risk."
 meta.append(dict(file=qa[0]['file'],title=title,description=desc,hashtags='#FootballPredictions #EuropaLeague #ConferenceLeague #MatchLedgerFootball',tags=['football predictions','5 November 2026','Monaco','Viktoria Plzen','Trabzonspor','Asian handicap','MatchLedger Football'],chapters=chapters))
 thumbnail=out/'matchledger-thumbnail-2026-11-05.png';graphic(scene('3 CAUTIOUS AH LEANS','',['MONACO / PLZEN / TRABZONSPOR','YESTERDAY: EVERY RESULT','05 NOV 2026 / EUROPEAN FOOTBALL']),thumbnail);im=Image.open(thumbnail);im.resize((1280,720)).save(thumbnail)
 for i,p in enumerate(d['predictions'][:3],1):
  e=p['evidence'];n=e['section_1_price']['n'];pct=e['price_weighted_wr'];team=p['home'] if p['selection']=='HOME' else p['away'];spoken=['Plzen minus a quarter','Trabzonspor draw no bet','Monaco minus one and a quarter'][i-1];match=['Lillestrom versus Plzen','Trabzonspor versus Freiburg','Monaco versus Nordsjaelland'][i-1]
  speech=f"{match}. Comparable handicap records: {pct} percent settlement weighted wins across {n} matches. Groups overlap; confidence stays cautious. Pick: {spoken}. MatchLedger Football."
  st=scene('THE STATISTICAL CASE',speech,pick=p,stat=[f'WEIGHTED WR {pct:.2f}%',f'N={n} / OVERLAPPING GROUPS']);stem=f'matchledger-short-{i:02}-2026-11-05';qa.append(render_video([st],out,stem,voice,True));graphic(st,out/(stem+'-cover.png'),True)
  meta.append(dict(file=stem+'.mp4',title=f'{team}: Why {label(p)}? | Football Predictions 5 Nov 2026 #Shorts',description=f"{names(p)}. Kickoff {p['kickoff']} UTC. Pick: {label(p)}. Matching price band settlement-weighted WR {pct:.2f}% across {n} historical records. Cautious editorial research lean. Groups overlap; historical WR is not this match's probability. Full episode: MatchLedger Football, 5 November 2026. Every Pick. Every Result. No guaranteed outcome.",hashtags='#Shorts #FootballPredictions #MatchLedgerFootball',tags=['football predictions','Asian handicap',team,'Shorts']))
 for m in meta:
  stem=Path(m['file']).stem;(out/(stem+'-metadata.txt')).write_text('TITLE\n'+m['title']+'\n\nDESCRIPTION\n'+m['description']+'\n\nHASHTAGS\n'+m['hashtags']+'\n\nTAGS\n'+', '.join(m['tags']))
 (out/'youtube-metadata.json').write_text(json.dumps(meta,indent=2));(out/'media-qa.json').write_text(json.dumps(qa,indent=2))
 for f in ep.iterdir():
  if f.is_file() and not f.name.endswith('.lock'):shutil.copy2(f,out/f.name)
 (out/'audio-license.txt').write_text('Kokoro ONNX local bm_george narration. Original synthesized instrumental music, no third party samples. No club crests or footage used. Underlying Kokoro model: Apache 2.0; model source thewh1teagle/kokoro-onnx release v1.0.')
 (out/'checksums.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()},indent=2))
if __name__=='__main__':main()
