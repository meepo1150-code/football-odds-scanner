"""Validate final encoded files, not a workflow success flag."""
import json,re,subprocess,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from .daily_v31 import probe
from .engine import read_ledger,label,settle

def command(args):return subprocess.run([str(a) for a in args],capture_output=True,text=True,check=True)
def main():
 out=Path('/workspace/scratch/18a186a533c8/deliverables');ep=Path('youtube_prediction/episodes/2026-11-06');d=json.loads((ep/'daily.json').read_text());ledger=read_ledger(ep/'prediction-ledger.jsonl');story=json.loads((ep/'reviewed-storyboard.json').read_text());report=[]
 for stem in ['matchledger-full-2026-11-06']+[f'matchledger-short-{i:02}-2026-11-06' for i in range(1,4)]:
  f=out/(stem+'.mp4');p=probe(f);vs=next(x for x in p['streams'] if x['codec_type']=='video');aus=next(x for x in p['streams'] if x['codec_type']=='audio');vertical='short-' in stem;size=(1080,1920) if vertical else (1920,1080);dur=float(p['format']['duration'])
  assert (vs['width'],vs['height'])==size and vs['codec_name']=='h264' and aus['codec_name']=='aac'
  if vertical:assert 15<=dur<=20
  command(['ffmpeg','-v','error','-xerror','-i',f,'-f','null','-'])
  sub=(out/(stem+'.srt')).read_text();ts=re.findall(r'(\d\d):(\d\d):(\d\d),(\d\d\d)',sub);times=[int(h)*3600+int(m)*60+int(s)+int(ms)/1000 for h,m,s,ms in ts];pairs=list(zip(times[::2],times[1::2]));assert pairs and all(0<=a<b<=dur+.05 for a,b in pairs);assert all(pairs[i][1]<=pairs[i+1][0]+.002 for i in range(len(pairs)-1))
  black=command(['ffmpeg','-hide_banner','-i',f,'-vf','blackdetect=d=0.4:pic_th=0.98:pix_th=0.05','-an','-f','null','-']).stderr
  assert 'black_start:' not in black
  audio=command(['ffmpeg','-hide_banner','-i',f,'-af','volumedetect','-vn','-f','null','-']).stderr
  mean=float(re.search(r'mean_volume: (-?[\d.]+)',audio).group(1));peak=float(re.search(r'max_volume: (-?[\d.]+)',audio).group(1));assert mean>-35 and peak>-10
  timeline=json.loads((out/(stem+'-timeline.json')).read_text());frame_dir=out/'qa-frames'/stem;frame_dir.mkdir(parents=True,exist_ok=True);images=[]
  for i,t in enumerate(timeline):
   time=t['start']+min(1.2,t['duration']/2);png=frame_dir/f'{i:02}.jpg';command(['ffmpeg','-y','-v','error','-ss',time,'-i',f,'-frames:v','1',png]);im=Image.open(png);im.thumbnail((480,330) if vertical else (480,270));images.append((im.copy(),i,t['kind']))
  # Contact sheets retain a readable view of every scene.
  columns=3 if vertical else 4;cellh=370 if vertical else 310;sheet=Image.new('RGB',(columns*480,((len(images)+columns-1)//columns)*cellh),'#081B31');dr=ImageDraw.Draw(sheet)
  for j,(im,i,kind) in enumerate(images):x=j%columns*480;y=j//columns*cellh;sheet.paste(im,(x,y));dr.text((x+10,y+cellh-28),f'{i:02} {kind}',fill='white')
  sheet.save(out/(stem+'-contact-sheet.jpg'))
  report.append(dict(file=f.name,duration=dur,width=size[0],height=size[1],video_codec=vs['codec_name'],audio_codec=aus['codec_name'],audio_mean_db=mean,audio_peak_db=peak,complete_decode='PASS',black_frame_check='PASS',subtitles='PASS',subtitle_cues=len(pairs),scene_frames_sampled=len(images),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),timeline=timeline))
  print('QA_PASS',f.name,dur,flush=True)
 for p in d['predictions']:
  r=next(x for x in ledger if x['prediction']['id']==p['id']);assert all(r['prediction'][k]==p[k] for k in r['prediction'])
 for r in json.loads((ep/'ft-settlement-report.json').read_text())['details']:assert r['settlement']==settle(r,*r['ft'])
 (out/'media-qa.json').write_text(json.dumps(report,indent=2));print('FINAL_MEDIA_QA_PASSED',flush=True)
if __name__=='__main__':main()
