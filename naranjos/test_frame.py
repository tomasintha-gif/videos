import time, numpy as np
from PIL import Image
from engine import Camera, render, billboard
import world as Wd
t0=time.time(); L=Wd.Lib(); print('lib',time.time()-t0)
shots=[
 ('day', Camera((-0.5,1.2,-6),(0,1.6,20),fov=60), 'normal','normal',False,False,None),
 ('night', Camera((-8,0.6,-3),(-8,2,20),fov=70), 'normal','blanket',True,True,Wd.grade_night),
 ('dawn', Camera((-20,22,-14),(-6,0,18),fov=60), 'ice','normal',False,False,Wd.grade_dawn),
]
for i,(sky,cam,hs,vs,sp,st,gr) in enumerate(shots):
    t0=time.time()
    em=[]
    items=Wd.orchard(L,cam,hs,vs,t=0.3,sprays=sp,stoves=st,emissive=em)
    items.append(billboard((-1,0,3),1.8,L.char('hero','surprised','up')))
    items.append(billboard((1,0,5),1.8,L.char('vecino','laugh','hip')))
    fog={'day':(150,190,230),'night':(30,44,90),'dawn':(230,200,190)}[sky]
    fr=render(cam,L.worlds[sky],items,fog,grade=gr,ground_tint=Wd.ice_ground if hs=='ice' else None,emissive=em)
    print(i,len(items),time.time()-t0)
    Image.fromarray(np.clip(fr,0,255).astype(np.uint8)).save(f'out/test{i}.jpg')
