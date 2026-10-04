#!/usr/bin/env python3
"""Render three representative pages of each newly retained unique deck."""
from __future__ import annotations
import csv,subprocess
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
MAN=ROOT/"dataset_acquisition"/"manifests"/"files.csv"
BASE=ROOT/"consulting_corpus"/"previews"
def main():
 with MAN.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
 for row in rows:
  if row.get("document_type")!="presentation" or row.get("format")!="PDF":continue
  src=ROOT/row["local_path"]
  count=int(row.get("page_or_slide_count") or 0)
  if not src.is_file() or count<1:continue
  pages=sorted({1,(count+1)//2,count})
  deck=BASE/row["file_id"];deck.mkdir(parents=True,exist_ok=True)
  rendered=[]
  for page in pages:
   dest=deck/f"page-{page:03d}"
   png=dest.with_suffix(".png")
   if not png.exists():
    subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),"-scale-to","960","-png","-singlefile",str(src),str(dest)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   rendered.append((page,png))
  thumbs=[]
  for page,png in rendered:
   im=Image.open(png).convert("RGB")
   target_h=510;target_w=round(im.width*target_h/im.height)
   im=im.resize((target_w,target_h))
   canvas=Image.new("RGB",(target_w,target_h+44),"white");canvas.paste(im,(0,44))
   ImageDraw.Draw(canvas).text((10,12),f"Page {page}",fill="black")
   thumbs.append(canvas)
  width=sum(im.width for im in thumbs)+24*(len(thumbs)+1)
  sheet=Image.new("RGB",(width,thumbs[0].height+48),"#e9edf2")
  x=24
  for im in thumbs:sheet.paste(im,(x,24));x+=im.width+24
  sheet.save(deck/"review-sheet.jpg",quality=90,optimize=True)
 print("Rendered representative pages for newly acquired PDF decks.")
if __name__=="__main__":main()
