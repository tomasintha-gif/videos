import sys, numpy as np, time
from PIL import Image
import render as R
R.init()
print('total', R.TOTAL, 'shots', len(R.STARTS))
fr_list=[]
which = [float(x) for x in sys.argv[1:]] or [0.55]
for i in range(len(R.STARTS)):
    for u in which:
        T = R.STARTS[i] + (R.ENDS[i]-R.STARTS[i])*u
        t0=time.time(); im = R.finish(R.frame_at(T), T); 
        fr_list.append(im.resize((270,480)))
cols=9; rows=(len(fr_list)+cols-1)//cols
s=Image.new('RGB',(270*cols,480*rows))
for k,im in enumerate(fr_list): s.paste(im,((k%cols)*270,(k//cols)*480))
s.save('out/contact.jpg',quality=88)
