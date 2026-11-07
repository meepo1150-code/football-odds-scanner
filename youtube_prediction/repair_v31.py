"""Re-render reviewed visual corrections; preserve original narration and ledger."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
from .daily_v31 import render_scene,run,probe,WHITE,MINT,text,shirt_image,short,background,load_story

def assemble(out,stem,vertical=False):
 work=out/(stem+'-work');joined=work/'joined-repaired.mp4';listing=work/'concat.txt';srt=out/(stem+'.srt')
 run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
 style=f"FontName=DejaVu Sans,FontSize={9 if vertical else 12},PrimaryColour=&H00FFFFFF,OutlineColour=&H00311B08,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV={54 if vertical else 20},MarginL=24,MarginR=24"
 vf=("drawbox=x=0:y=1435:w=iw:h=62:color=0x0B263B:t=fill," if vertical else '')+f"subtitles='{srt.resolve()}':force_style='{style}'"
 final=out/(stem+'.mp4')
 run(['ffmpeg','-y','-v','error','-i',joined,'-i',work/'music.wav','-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.10[a]','-map','0:v','-map','[a]','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',final])
 run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-']);print('REPAIRED',final.name,probe(final)['format']['duration'],flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--episode',required=True);ap.add_argument('--output',required=True);ap.add_argument('--shorts-only',action='store_true');a=ap.parse_args();ep=Path(a.episode);out=Path(a.output).resolve();d=json.loads((ep/'daily.json').read_text());story=load_story(ep,d)
 if a.shorts_only:
  for i in range(1,4):assemble(out,f'matchledger-short-{i:02}-'+d['date'],True)
  return
 stem='matchledger-full-'+d['date'];work=out/(stem+'-work')
 class CachedVoice:
  def synthesize(self,speech,path):assert path.is_file();return []
 for i in [0,2,8,12,16,20]:render_scene(story['full'][i],i,work,CachedVoice())
 assemble(out,stem)
 thumb=out/('matchledger-thumbnail-'+d['date']+'.png');background(thumb);im=Image.open(thumb).convert('RGBA');dr=ImageDraw.Draw(im)
 text(dr,(80,210),'4 CAUTIOUS RESEARCH LEANS',92,MINT,True,1760);text(dr,(80,340),'06 NOV 2026 / YESTERDAY: 2 WINS + 1 LOSS',46,WHITE,True,1760)
 for i,p in enumerate(d['predictions']):
  f=work/f'thumb-shirt-{i}.png';shirt_image(p['home'],f);sh=Image.open(f).resize((300,330));x=140+450*i;im.alpha_composite(sh,(x,480));text(ImageDraw.Draw(im),(x-30,850),short(p['home']),37,WHITE,True,400)
 im.convert('RGB').resize((1280,720)).save(thumb)
if __name__=='__main__':main()
