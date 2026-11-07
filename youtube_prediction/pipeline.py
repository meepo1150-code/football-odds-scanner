"""One-command isolated production. No scanner or provider calls."""
import argparse
import asyncio
import json
import math
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from .engine import TZ, append_ledger, fingerprint, iso_time, label, read_ledger, summarize, validate, verify_fixtures

WIDTH, HEIGHT = 1920, 1080

def read_json(path):
    return json.loads(Path(path).read_text())

def jsonl(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]

def run(args, **kw):
    subprocess.run(args, check=True, **kw)

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def render_card(path, heading, lines, footer):
    from PIL import Image, ImageDraw, ImageFont
    fontpath = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    image = Image.new('RGB',(WIDTH,HEIGHT),(8,17,34)); d = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        d.line((0,y,WIDTH,y),fill=(8+int(y/90),17+int(y/65),34+int(y/50)))
    d.rounded_rectangle((72,70,1848,1008),radius=32,outline=(46,76,105),width=3)
    d.rectangle((72,70,88,1008),fill=(60,220,183))
    def fit(text, size, maxwidth):
        while size >= 22:
            f=ImageFont.truetype(fontpath,size)
            if d.textbbox((0,0),text,font=f)[2] <= maxwidth: return f
            size-=2
        raise ValueError('Text too long to render safely')
    d.text((125,120),heading,font=fit(heading,72,1640),fill='white')
    d.line((125,225,1790,225),fill=(60,220,183),width=4)
    if len(lines)>6: raise ValueError('Slide needs pagination')
    for i,text in enumerate(lines):
        d.text((130,290+i*92),text,font=fit(text,49,1630),fill=(224,236,246))
    d.text((130,930),footer,font=fit(footer,29,1630),fill=(139,174,198))
    image.save(path)

def scenes(data, summary):
    result=[]
    def add(heading,lines,speech): result.append(dict(heading=heading,lines=lines,speech=speech))
    add('FOOTBALL DAILY',[data['date'],'Predictions & results','All kickoff times: Bangkok (UTC+7)'],f"Welcome to Football Daily for {data['date']}. Here is your football predictions and results briefing. All kickoff times are Bangkok time.")
    if not summary['details']:
        add("YESTERDAY'S RESULTS",['No archived predictions for '+summary['yesterday'],'Win rate: not available'],"There are no archived predictions for yesterday in this ledger. A win rate is not available.")
    for p in summary['details']:
        ft='Pending' if p['ft'] is None else f"{p['ft'][0]} - {p['ft'][1]}"
        outcome=p['settlement'].replace('_',' ').title()
        add("YESTERDAY'S RESULTS",[p['home']+' vs '+p['away'],label(p),'Full time: '+ft,outcome],f"{p['home']} versus {p['away']}. The archived pick was {label(p)}. Full time: {ft}. Result: {outcome}.")
    if summary['details']:
        lines=[]; words=[]
        for market in ('AH','OU'):
            for period in ('daily','cumulative'):
                s=summary[period][market]; value='N/A' if s['wr'] is None else f"{100*s['wr']:.1f}%"
                lines.append(f"{market} {period.title()} WR: {value}")
                words.append(f"{market} {period} weighted win rate: {value}.")
        add('RESULTS SCORECARD',lines,' '.join(words))
    if not data['predictions']:
        add("TODAY'S PREDICTIONS",['No reviewed predictions supplied','No picks added to the record'],"No reviewed predictions have been supplied for today's episode. We will not add unverified picks.")
    for p in data['predictions']:
        time=iso_time(p['kickoff']).astimezone(TZ).strftime('%d %b, %H:%M')
        add("TODAY'S PREDICTIONS",[p['home']+' vs '+p['away'],'Kickoff: '+time+' Bangkok',label(p)],f"{p['home']} versus {p['away']}. Kickoff {time}, Bangkok time. The prediction is {label(p)}.")
    picks=data['predictions']
    for start in range(0,max(1,len(picks)),4):
        group=picks[start:start+4]
        lines=[p['home']+' vs '+p['away']+' | '+label(p) for p in group] or ['No picks in this episode']
        speech='Today’s picks recap. '+(' '.join(p['home']+' versus '+p['away']+'. '+label(p)+'.' for p in group) if group else 'There are no picks in this episode.')
        add('DAILY PICKS RECAP',lines,speech)
    add('SEE YOU NEXT TIME',['Follow the picks. Track the results.','No guaranteed outcomes.'],"Thanks for watching. Join us for the next football briefing and the results of our recorded picks. No prediction guarantees an outcome.")
    return result

def stamp(seconds):
    n=round(seconds*1000); h,n=divmod(n,3600000); m,n=divmod(n,60000); s,ms=divmod(n,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

async def speak(text,path,voice):
    import edge_tts
    # Extend trust with an explicitly configured corporate CA, never disable TLS.
    if os.environ.get('SSL_CERT_FILE'):
        import edge_tts.communicate
        edge_tts.communicate._SSL_CTX.load_verify_locations(os.environ['SSL_CERT_FILE'])
    async def generate():
        boundaries=[]
        with Path(path).open('wb') as output:
            async for event in edge_tts.Communicate(text,voice,rate='-5%',boundary='WordBoundary').stream():
                if event['type']=='audio': output.write(event['data'])
                elif event['type']=='WordBoundary': boundaries.append(event)
        if not boundaries: raise ValueError('TTS word timing missing')
        return boundaries
    return await asyncio.wait_for(generate(),timeout=90)

def music(path,duration):
    """Original procedural ambient score, no samples or third-party music."""
    import numpy as np
    import wave
    rate=24000; t=np.arange(math.ceil(duration*rate))/rate
    notes=[130.8128,164.8138,195.9977,146.8324]
    audio=np.zeros(len(t))
    for i,f in enumerate(notes): audio+=.022*np.sin(2*np.pi*f*t)*(.6+.4*np.sin(2*np.pi*.07*t+i))
    audio*=np.minimum(t/2,1)*np.minimum((duration-t)/2,1)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes((audio*32767).astype('<i2').tobytes())

def build(data,out,ledger,fixtures=(),results=(),voice='en-US-GuyNeural'):
    validate(data); verify_fixtures(data,fixtures)
    # Validate FT and old archive before any mutation.
    old=read_ledger(ledger); summary=summarize(old,results,data['date'])
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()): raise ValueError('Use a new empty output directory')
    n=append_ledger(ledger,data,fixtures)
    script=scenes(data,summary)
    (out/'input.json').write_text(json.dumps(data,indent=2))
    (out/'results.json').write_text(json.dumps(summary,indent=2))
    (out/'script.json').write_text(json.dumps(script,indent=2))
    report=['# Football Daily — '+data['date'], '', '## ผลเมื่อวาน',json.dumps(summary,ensure_ascii=False,indent=2),'','## วิเคราะห์วันนี้']
    report += [p['home']+' vs '+p['away']+' — '+label(p)+' — '+iso_time(p['kickoff']).astimezone(TZ).strftime('%d/%m %H:%M')+' Bangkok' for p in data['predictions']] or ['ไม่มีข้อมูลคำทำนายที่ผ่านการตรวจส่งเข้ามาสำหรับวันนี้']
    (out/'report.md').write_text('\n'.join(report))
    elapsed=0; subtitles=[]; timeline=[]
    for i,scene in enumerate(script):
        stem=f'scene-{i:03}'
        render_card(out/(stem+'.png'),scene['heading'],scene['lines'],'FOOTBALL DAILY  |  '+data['date']+'  |  Bangkok UTC+7')
        boundaries=asyncio.run(speak(scene['speech'],out/(stem+'.mp3'),voice))
        duration=math.ceil((float(probe(out/(stem+'.mp3'))['format']['duration'])+.6)*30)/30
        for k in range(0,len(boundaries),8):
            group=boundaries[k:k+8]
            start=elapsed+group[0]['offset']/10000000
            end=elapsed+(group[-1]['offset']+group[-1]['duration'])/10000000
            chunk=' '.join(w['text'] for w in group)
            subtitles.append(f'{len(subtitles)+1}\n{stamp(start)} --> {stamp(end)}\n{chunk}\n')
        timeline.append(dict(start=elapsed,duration=duration,**scene)); elapsed+=duration
        run(['ffmpeg','-y','-v','error','-loop','1','-i',str(out/(stem+'.png')),'-i',str(out/(stem+'.mp3')),'-t',str(duration),'-vf',"zoompan=z='min(zoom+0.000025,1.012)':d=1:s=1920x1080:fps=30,fade=t=in:st=0:d=0.3,format=yuv420p",'-af','apad,loudnorm=I=-16:TP=-1.5:LRA=11','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','2','-c:a','aac','-ar','48000','-ac','2',str(out/(stem+'.mp4'))])
    (out/'subtitles.srt').write_text('\n'.join(subtitles))
    (out/'timeline.json').write_text(json.dumps(timeline,indent=2))
    (out/'concat.txt').write_text(''.join(f"file 'scene-{i:03}.mp4'\n" for i in range(len(script))))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','concat.txt','-c','copy','joined.mp4'],cwd=out)
    music(out/'music.wav',elapsed)
    run(['ffmpeg','-y','-v','error','-i','joined.mp4','-i','music.wav','-filter_complex',"[0:a][1:a]amix=inputs=2:duration=first:weights='1 0.35'[a];[0:v]subtitles=subtitles.srt:force_style='FontSize=19,MarginV=58,Outline=2'[v]",'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','21','-threads','2','-c:a','aac','-movflags','+faststart','video.mp4'],cwd=out)
    render_card(out/'thumbnail.png','FOOTBALL DAILY',[data['date'],f"{len(data['predictions'])} reviewed picks" if data['predictions'] else 'Daily briefing','Predictions + results'],'ENGLISH EDITION')
    from PIL import Image
    with Image.open(out/'thumbnail.png') as im: im.resize((1280,720)).save(out/'thumbnail.jpg',quality=92)
    metadata=dict(title='Football Daily | '+data['date'],description='Reviewed football predictions and recorded results. All times Bangkok (UTC+7). No guaranteed outcomes. AI-generated narration. Original procedural background music. '+summary['wr_definition'],tags=['football','football predictions','daily football'],privacyStatus='private',defaultLanguage='en')
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2))
    (out/'MUSIC_LICENSE.txt').write_text('Original procedural composition generated by youtube_prediction.pipeline.music. No samples, recordings, or third-party compositions used. Project owner may use this generated score in these videos.\n')
    info=probe(out/'video.mp4'); video=next(s for s in info['streams'] if s['codec_type']=='video'); audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    if (video['width'],video['height'])!=(1920,1080) or abs(float(info['format']['duration'])-elapsed)>1: raise ValueError('Video QA failed')
    run(['ffmpeg','-v','error','-i',str(out/'video.mp4'),'-f','null','-'])
    manifest=dict(video_created=True,audio_created=True,qa_decode_passed=True,width=1920,height=1080,duration=float(info['format']['duration']),predictions=len(data['predictions']),ledger_records_appended=n,ledger_head=read_ledger(ledger)[-1]['hash'] if read_ledger(ledger) else None,voice=voice,youtube_uploaded=False,subtitle_timing='TTS word boundaries; human listening review required',files={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)); return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); p.add_argument('--ledger',required=True); p.add_argument('--fixtures',required=True); p.add_argument('--results',required=True); p.add_argument('--voice',default='en-US-GuyNeural'); a=p.parse_args()
    print(json.dumps(build(read_json(a.input),Path(a.output),Path(a.ledger),jsonl(a.fixtures),jsonl(a.results),a.voice),indent=2))
