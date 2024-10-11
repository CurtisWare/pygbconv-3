This is an updated version of Nitro2k01's pygbconv python script. It's almost the same, except it uses some more
Python 3-esque syntax, certain variables are converted to bytes before they are concatenated, and maps are passed
into arguments as lists.
 
A difference is that the original Python 2.7 version does not fail emulator rom header checks. I'm not sure how to fix this,
but the rom still works fine on emulators and hardware.

EXAMPLE USAGE:

In your terminal/cmd prompt, change directory to where this script and your images are stored.
Say you have 3 images you want to use, called image1.png, image2.png and image3.png.
Type the following into the terminal:

python pygbconv.py out.gb image1.png image2.png image3.png
