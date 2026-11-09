"""Offline neural narration. Reads model files; performs no network requests."""
import re
import textwrap
import wave
from pathlib import Path
import numpy as np
from kokoro_onnx import Kokoro

class LocalVoice:
    def __init__(self,model,voices):
        if not Path(model).is_file() or not Path(voices).is_file():raise ValueError('Download public model files before production')
        self.engine=Kokoro(str(model),str(voices))
    def synthesize(self,text,path):
        parts=re.split(r'(?<=[.!?])\s+',text.strip())
        audio=[];captions=[];cursor=0;rate=24000
        for sentence in parts:
            spoken=sentence.replace('Willem II','Willem two').replace('PEC Zwolle','P E C Zwolle').replace(' v ',' versus ').replace('Vejle','Vay luh').replace('17:00','seventeen hundred').replace('19:00','nineteen hundred').replace('19:30','nineteen thirty')
            samples,rate=self.engine.create(spoken,voice='bm_george',speed=1.04,lang='en-gb',sentence_pause=.12,clause_pause=.08)
            duration=len(samples)/rate
            lines=textwrap.wrap(sentence,width=66)
            if len(lines)>2:
                # Keep captions readable; alignment is at measured sentence boundaries.
                middle=len(lines)//2
                chunks=['\n'.join(lines[:middle]),'\n'.join(lines[middle:])]
                for j,chunk in enumerate(chunks):captions.append(dict(start=cursor+j*duration/2,end=cursor+(j+1)*duration/2,text=chunk))
            else:captions.append(dict(start=cursor,end=cursor+duration,text='\n'.join(lines)))
            pause=np.zeros(int(rate*.12),dtype=np.float32)
            audio.extend([samples,pause]);cursor+=duration+.12
        samples=np.concatenate(audio)
        with wave.open(str(path),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
        return captions
