"""Correct speech within existing scene timing and preserve canonical captions."""
import json,re
from pathlib import Path
from .local_voice import LocalVoice
from .daily_v31 import probe,run,load_story,art,stamp
from .repair_v31 import assemble

def parse_srt(p):
 out=[]
 for block in p.read_text().strip().split('\n\n'):
  lines=block.splitlines()
  if len(lines)<3:continue
  t=re.findall(r'(\d\d):(\d\d):(\d\d),(\d\d\d)',lines[1]);v=[int(h)*3600+int(m)*60+int(s)+int(ms)/1000 for h,m,s,ms in t];out.append((v[0],v[1],'\n'.join(lines[2:])))
 return out

def main():
 ep=Path('youtube_prediction/episodes/2026-11-06');out=Path('/workspace/scratch/18a186a533c8/deliverables');data=json.loads((ep/'daily.json').read_text());story=load_story(ep,data);voice=LocalVoice('/workspace/scratch/18a186a533c8/voice/model.onnx','/workspace/scratch/18a186a533c8/voice/voices.bin');audit=[]
 for stem,ss in [('matchledger-full-2026-11-06',story['full'])]+[(f'matchledger-short-{i:02}-2026-11-06',p['scenes']) for i,p in enumerate(story['shorts'],1)]:
  work=out/(stem+'-work');timeline=json.loads((out/(stem+'-timeline.json')).read_text());srt=out/(stem+'.srt');cues=parse_srt(srt);vertical='short-' in stem
  indices=[i for i,s in enumerate(ss) if any(x in s['speech'] for x in [' v ','Vejle','Willem II','17:00','19:00','19:30'])]
  for i in indices:
   s=ss[i];t=timeline[i];new=work/f'{i:02}-voice-corrected.wav';caps=voice.synthesize(s['speech'],new);nd=float(probe(new)['format']['duration']);old=work/f'{i:02}.wav';od=float(probe(old)['format']['duration']);ratio=nd/od;assert .70<ratio<1.3
   adjusted=work/f'{i:02}-voice-adjusted.wav';run(['ffmpeg','-y','-v','error','-i',new,'-af',f'atempo={ratio},apad','-t',od,adjusted])
   part=work/f'{i:02}.mp4';fixed=work/f'{i:02}-corrected.mp4';run(['ffmpeg','-y','-v','error','-i',part,'-i',adjusted,'-map','0:v','-map','1:a','-c:v','copy','-af','apad,loudnorm=I=-16:TP=-1.5:LRA=9','-t',t['duration'],'-c:a','aac','-ar','48000','-ac','2',fixed]);fixed.replace(part)
   start=t['start'];end=start+t['duration'];cues=[c for c in cues if c[0]<start-.01 or c[0]>=end-.01]
   for c in caps:
    words=c['text'].replace('\n',' ').split();lines=[];line=''
    for word in words:
     if len(line+' '+word)>(34 if vertical else 64):lines.append(line);line=word
     else:line=(line+' '+word).strip()
    if line:lines.append(line)
    groups=['\n'.join(lines[j:j+2]) for j in range(0,len(lines),2)];total=sum(len(g) for g in groups);cursor=c['start']/ratio
    for group in groups:
     ce=cursor+(c['end']-c['start'])/ratio*len(group)/total;cues.append((start+cursor,min(start+ce,end-.01),group));cursor=ce
   audit.append(dict(file=stem,scene=i,speech=s['speech'],tempo_ratio=ratio));print('VOICE_FIXED',stem,i,flush=True)
  if not vertical:
   i=21;t=timeline[i];png=work/'21-panel.png';art(ss[i],png);recap=work/'21-recap-visual.mp4'
   run(['ffmpeg','-y','-v','error','-loop','1','-framerate','24','-i',work/'background.png','-loop','1','-framerate','24','-i',png,'-i',work/'21.mp4','-filter_complex_threads','1','-filter_complex',"[0:v][1:v]overlay=x='-60*max(0,1-t/0.35)':y=0,fade=t=in:d=0.12,format=yuv420p[v]",'-map','[v]','-map','2:a','-t',t['duration'],'-c:v','libx264','-preset','ultrafast','-crf','22','-threads','2','-c:a','copy',recap]);recap.replace(work/'21.mp4')
  cues.sort();srt.write_text('\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{c}\n' for i,(a,b,c) in enumerate(cues)));assemble(out,stem,vertical)
 (out/'pronunciation-qa.json').write_text(json.dumps(audit,indent=2));print('PRONUNCIATION_CORRECTIONS_COMPLETE',flush=True)
if __name__=='__main__':main()
