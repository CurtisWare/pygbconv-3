# This is an updated version of Nitro2k01's pygbconv python script. It's almost the same, except it uses some more
# Python 3-esque syntax, certain variables are converted to bytes before they are concatenated, and maps are passed
# into arguments as lists.
# 
# A difference is that the original Python 2.7 version does not fail emulator rom header checks. I'm not sure how to fix this,
# but the rom still works fine on emulators and hardware.

# EXAMPLE USAGE:
# python pygbconv.py out.gb image1.png image2.png image3.png

import sys
from PIL import Image
from collections import defaultdict
from math import floor, ceil, log

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    # print(l)
    for i in range(0, len(list(l)), n):
        yield list(l)[i:i+n]

# Takes a size 64 tuple and returns 16 bytes in GB tile format
def convtile(tile_in):
    # print(tile_in)
    lines = chunks(tile_in, 8)
    tempstring = b""
    
    for l in lines:
        lowerbyte = ""
        upperbyte = ""
        
        for b in l:
            lowerbyte += "1" if (b & 1) else "0"
            upperbyte += "1" if (b & 2) else "0"
    
        tempstring += bytes([int(lowerbyte, 2), int(upperbyte, 2)])
    
    return tempstring

def convimg(name):
    print(f"===Processing {name}")
    img = Image.open(name)
    
    w, h = img.size
    
    if (w != 160 or h != 144):
        print("Image must be exactly 160*144 big")
        sys.exit()

    # Convert the image to RGB
    img = img.convert('RGB')    
    pixels = img.getdata()
    colors = []
    # Analyze the color content of the image
    for pxl in pixels:
        if not pxl in colors:
            colors.append(pxl)
        
        if len(colors) > 4:
            break

    
    # Exit or warn if the number of colors isn't exactly 4
    if len(colors) > 4:
        print("Image must contain no more than 4 unique colors.")
        sys.exit()
    elif len(colors) < 4:
        print(f"Warning! Image has only {len(colors)} unique colors (instead of exactly 4).")

    # Sort colors by brightness
    colors = sorted(colors, key=lambda c: c[0] + c[1] + c[2])

    # Fill up the color table if the image has fewer colors
    if len(colors) == 2:
        colors = [colors[0], colors[1], colors[1], colors[1]]
    elif len(colors) == 3:
        colors = [colors[0], colors[1], colors[1], colors[2]]
    elif len(colors) == 1:
        print("Warning: This image only has a single, solid color.")
        colors = [colors[0], colors[0], colors[0], colors[0]]

    colors_r = defaultdict(int)
    
    # Create reverse lookup table for color -> GB color index
    for i, color in enumerate(colors): 
        colors_r[color] = i

    # Convert RGB pixels to an array consisting of values 0-3
    pixels_g = map(lambda x: colors_r[x], pixels)
    # Slice up the image in tile-sized chunks (8*8)
    
    # For Python 3, pixels_g needed to be passed in as a list
    pixels_g = chunks(list(pixels_g), w * 8) 
  
  
    # Slice up the rows of 8 pixels to tiles
    tiles = []

    # Iterate through each row of 8 pixel height
    for row in pixels_g:
        
        # Iterate through the number of tiles defined by the width
        for j in range(20): #int(w / 8)
            temp = []
            # Iterate through 8 pieces of 8*1 pixel segments which together form a tile
            for k in range(8):
                temp += row[j*8+k*w:j*8+k*w+8]
            tiles.append(temp)
    
    # Convert tiles into binary format used in Gameboy
    # Converting the map to a list for Python 3
    tiles = list(map(convtile, tiles))

    # Reverse lookup tile table to look for duplicate tiles that can be optimized away
    tilemap = []
    tiles_o = []
    
    for t in tiles:
        # If tile doesn't exist in optimized tile set, add it
        if not t in tiles_o:
            tiles_o.append(t)
        
        # Add the tile to the map
        tilemap.append(tiles_o.index(t))
    
    # Convert to binary
    tilemap = b"".join(bytes([x & 0xff]) for x in tilemap)
    
    if len(tiles_o) > 256:
        print("Could not optimize image to below 256 tiles.")
        tiles = b"".join(x for x in tiles)
        return tiles, None
    else:
        print(f"Optimized image to {len(tiles_o)} tiles.")
        tiles_o = b"".join(x for x in tiles_o)
        return tiles_o, tilemap

def db(val):
    return bytes([val & 0xff])

def dw(val):
    return bytes([val & 0xff, (val >> 8) & 0xff])

def dw_flip(val):
    return bytes([(val >> 8) & 0xff, val & 0xff])

def gbheaderchecksum(r):
    acc = 0
    for i in r[0x134:0x14d]:
        acc += ~i & 0xff
        acc &= 0xff
    
    return db(acc)

def gbglobalchecksum(r):
    acc = 0
    for i in r:    
        acc += i
        acc &= 0xffff
    
    return dw_flip(acc)

def gbromfix(romdata):
    # Calculate header value for the ROM size
    romsize = int(ceil(log(len(romdata), 32768)))
    
    # Restore target size that the ROM should be padded up to
    targetsize = 32768 << romsize

    # How many bytes are missing
    missingbytes = targetsize - len(romdata)

    # Append that many bytes
    romdata += b'\xff' * missingbytes

    # Modify header values
    romdata = bytearray(romdata)
    romdata[0x148] = romsize           # ROM size header value
    romdata[0x14d] = gbheaderchecksum(romdata)[0]   # Header checksum
    romdata[0x14e:0x150] = gbglobalchecksum(romdata)
    
    return bytes(romdata)

# Preamble IMG
def compilerom(gbin, gbout, images):
    gbtiles = map(convimg, images)
    # Using Python3 syntax for opening file
    with open(gbin, "rb") as f:
        baserom = f.read(16384)
    
    # For Python 3 version, setting these explicity to bytes, because strings and bytes cannot be concatenated
    headerpart = b"IMG"
    gfxpart = b""
    
    headersize = 4 * len(images) + 3 + 1
    
    for gt in gbtiles:
        accum = headersize + len(gfxpart)
        bank = (accum >> 14) + 1
        startaddr = accum % 16384 + 16384
        
        if gt[1] is None:
            numtiles = 0
            gfxpart += gt[0]
        else:
            numtiles = max(1, len(gt[0]) // 16 - 1)
            gfxpart += gt[1] + gt[0]
    
        headerpart += db(bank) + dw(startaddr) + db(numtiles)
        
    headerpart += b'\x00'

    # Write to output file
    with open(gbout, "wb") as fout:
        fout.write(gbromfix(baserom + headerpart + gfxpart))

if len(sys.argv) < 3:
    print("Usage: ./pygbconv.py output.gb image0.png image1.png ...")
elif len(sys.argv) > 258:
    print("Please keep it under 256 images!")
else:
    compilerom("imagerom.gbbase", sys.argv[1], sys.argv[2:])
