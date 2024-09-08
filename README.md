# simple-PID
simple PID RPI
Made for rassbberry pi kiln controller ssimple PID
download zip unzip to main pi home directory 

install
in terminal copy paste 

$    cd melttech
$    python3 -m venv venv
$    source venv/bin/activate
$    pip install -r requirements.txt

that will install it now to run it in terminal type or copy  paste one line at a time below

$    cd melttech
$    source venv/bin/activate
$    python kiln_controller.py

then open web browser open program with

http://127.0.0.1:5001/

that easy

to get it on your phone put in ip adresss of youur PI example below

Running on http://192.168.0.166:5001


Works with Maxx31855 chip only even works  grounding out thermocouple

Max31855 chip settings 

css 8
clk 11
do 9

relay pin for heat pin set to     pin 20

you can change these edit main file
TURN ON SPI SETTINGS ON YOUR RPI SETTINGS IN RASPBERRY PI ONFIGURATTIONS UNDER INTERFACES

IF it gets a board error try manual install file in download install drivers one at a time see files for manual install!!!!!

made by MeltTech 2024
