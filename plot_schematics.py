"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = .92 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def pipeline(out):
    d=Drawing((0,0,16.4,6.9))
    for a in [
        ('snap',1.9,4.7,3.1,1.0,'Tagged source\nsnapshots'),
        ('origin',8.0,4.7,4.0,1.0,'Anchored origins\nand facts'),
        ('horn',14.2,4.7,3.3,1.0,'Fixed Horn\nrules'),
        ('history',8.0,6.2,4.0,.8,'Declared changes'),
        ('bridge',14.2,6.2,3.3,.8,'Explicit bridges'),
        ('front',14.2,1.5,3.3,1.0,'Minimal-support\nfrontiers'),
        ('joint',8.0,1.5,4.0,1.0,'Minimum-cost\njoint union'),
        ('cert',1.9,1.5,3.1,1.0,'Proof-carrying\ncertificate')]:
        d.box(*a)
    d.edge('snap','origin','e','w')
    d.edge('origin','horn','e','w')
    d.edge('history','origin')
    d.edge('bridge','horn')
    d.edge('horn','front')
    d.edge('front','joint','w','e')
    d.edge('joint','cert','w','e')
    d.arrow(d.point('cert','w'),d.point('origin','s'),dashed=True,
            via=((.15,1.5),(.15,3.1),(8,3.1)))
    d.text(8.7,2.75,'Replay: anchors, proofs, union cost, bounded optimum',8)
    d.save(out,'pipeline')

def running(out):
    d=Drawing((0,0,16.4,6.3))
    d.box('old',1.8,5.1,3.2,.9,'Old span $o$ (cost 2)')
    d.box('change',1.8,3.1,3.2,.9,'Change $h$ (cost 1)')
    d.box('new',1.8,1.1,3.2,.9,'New span $n$ (cost 2)')
    d.box('a0',5.8,5.1,.85,.85,'$a_0$',shape='circle')
    d.box('a1',5.8,1.1,.85,.85,'$a_1$',shape='circle')
    d.box('bridge',5.8,3.1,3.0,.9,'Bridge $b$ (cost 1)')
    d.box('e',9.0,3.1,.85,.85,'$e$',shape='circle')
    d.box('rp',11.8,5.1,1.0,1.0,'$r_+$',shape='diamond')
    d.box('rn',11.8,1.1,1.0,1.0,'$r_-$',shape='diamond')
    d.box('p',15.0,5.1,.85,.85,'$p$',shape='circle')
    d.box('np',15.0,1.1,.85,.85,r'$\overline{p}$',shape='circle')
    for a,b in [('old','a0'),('change','a0'),('change','a1'),('new','a1'),
                ('bridge','e'),('a0','rp'),('a1','rn'),('e','rp'),('e','rn'),
                ('rp','p'),('rn','np')]:
        d.edge(a,b,'e','w')
    d.text(8.2,.25,r'Selected union $\{o,h,n,b\}$: shared $h$ and $b$ are charged once',8)
    d.save(out,'running-example')

def main():
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
    out=p.parse_args().outdir;out.mkdir(parents=True,exist_ok=True)
    pipeline(out);running(out)
if __name__=='__main__':
    main()
