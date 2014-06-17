# -*- coding: utf-8 -*-
"""
GCGen: G Code Generator for StrongPrint Created on Mon May  5 02:43:35 2014

@author: kolergy

Simple tool to generate GCode adapted to perform tests with the StrongPrint 3DPrinter

ChangeLog:
- V0.7: Added DryRun option
"""
import math

# settings
# This is where you modify the settings for a test print
# At terms this should be moved in a json set-up file
setupData = {
    "DryRun":         False,   # If DryRun true, do not extrude the wire
    "MaxZ":           320.0,   # (mm) Height of the machine 
    "PrintRadius":    300.0,   # (mm) Printable radius 
    "Z0":               5.55,   # (mm) correction of the zero
    "WeldHeight":       1.9,   # (mm) distance between weld tip & part
    "ApproachHeight":  10.0,   # (mm) safe height for approach
    "TravelHeight":     5.0,   # (mm) safe height for travel with arc
    
    "ColdWeldSpeed":   30.0,   # (mm/min) speed while welding
    "WeldSpeedHot":     0.5,   # (-) ratio of hot weld speed to cold
    "HotLength":       40.0,   # (mm) length over which the speed ratio is varied
    "WeldSpeedUp":      0.5,   # (%/s)  percentage of speed increase per seconds for welding
    "TravelSpeed":   5000.0,   # (mm/min) travel speed 
    
    "ExtrMxSpeed":   5000.0,   # (mm/min) Max wire speed
    
    "Acceleration":   100.0,   # (mm/s^2) Default Acceleration for the machine
    
    "PuddleTime":       2.5,   # (s) Time stationary to create the weld puddle
    "ExtrusionFactor":  0.8,   # (-) Multiplier of filament extruded over length
    "RetractionLen":    1.4,   # (mm)
    "Retractionfactor": 1.005, # (mm) disymetry between retract & extrude
    "RetractionPlay":   1.8,   # (mm)
    "RetractionTravel": 0.15,  # (mm)
    
    
    "GCodeFileName": "AUTO.gcode",   # The output file name
    
    "IgnitCoord": { "x":-50.0, "y":15.0, "len": 30.0 },  # initial coordinates
 }
      
workData = {    # not used yet
        "Task001": {
            "Type": "line",
            "Points": [ { "x": 0.0, "y": 10.0, "len": 50.0, "angl": 30.0}]
        },
        "Task002": {
            "Type": "rect",
            "Points": [ { "x": 0.0, "y": 20.0}, { "x": 50.0, "y": 30.0}]
        },
    }

# Global variables should not be modified
E         = 0  # (mm)  Extrusion length  
lastPoint = {"x": None, "y": None, "z": None}  # store the position after each move

# some premitives for testing
def circle(x, y, r, n=20):
     print "  ## circle(x, y, r) ##"
     li = []
     a  = 2 * math.pi / n 
     for i in range(0, n+1): 
         ai = a * i
         Xi = x + r * math.cos(ai)
         Yi = y + r * math.sin(ai)
         li.append([Xi, Yi])
         print "[ " + str(Xi) + "\t, " + str(Yi) + "]"
     #print li
     return li
     
def line(x, y, l, a):
     print "  ## line(x, y, l, a) ##"
     li = [[x, y], [x+l*math.cos(math.radians(a)), y+l*math.sin(math.radians(a))]]
     print li
     return li
   
def calcTime(speed, dist): # not correct but should be relatively proportional
    t = dist / speed
    return t
   
# Generate the move command with optional parameters
def move(x=None, y=None, z=None, e=None, speed=None, comment=None):
    #print "  ## move() ##"
    global lastPoint
    s = "G1 "
    if x is not None: 
        s += "X" + str(x) + " "
        lastPoint["x"] = x 
    if y is not None: 
        s += "Y" + str(y) + " "
        lastPoint["y"] = y 
    if z is not None: 
        s += "Z" + str(z) + " "
        lastPoint["z"] = z 
    if e is not None: s += "E" + str(e) + " "
    
    if speed is not None: 
        if speed == "Weld"  : s += "F" + str(setupData["WeldSpeed"  ]) + " "
        if speed == "Travel": s += "F" + str(setupData["TravelSpeed"]) + " "
        
    if comment is not None:  s += "; " + comment
    
    s += "\n"
    return s

# print a single segments
def printSegment(X1, Y1, X2, Y2):
    #print "  # printSegment(X1, Y1, X2, Y2) #"
    printSeg  = "; Segment starts\n"
    
    global E
    global setupData
    dX    = X2 - X1
    dY    = Y2 - Y1
    dL    = math.sqrt(dX**2+dY**2)
    steps = int(dL / setupData["RetractionTravel"])
    dXi   = dX/steps
    dYi   = dY/steps
    dl    = math.sqrt(dXi**2+dYi**2)
    l     = 0.0
    
    if setupData["DryRun"]:
        ret = 0.0
        ex  = 0.0
    else:
        ret = setupData["RetractionLen"] + setupData["RetractionPlay"]
        ex  = ret*setupData["Retractionfactor"] + 2*dl * setupData["ExtrusionFactor"]  # calculate extrusion to perform

    for i in range(0, steps):
        l += math.sqrt(dXi**2 + dYi**2)
        setupData["WeldSpeed"] = setupData["ColdWeldSpeed"] + setupData["ColdWeldSpeed"] * setupData["WeldSpeedHot"] * min(l/setupData["HotLength"] , 1)
        print "WS:%f" % setupData["WeldSpeed"]
        E += ex
        printSeg += move( e=E, speed="Travel", comment="Weld"   )
        E += -ret
        printSeg += move( e=E, speed="Travel", comment="Retract")
        printSeg += move( x=lastPoint["x"] + dXi, y=lastPoint["y"] + dYi,  speed="Weld", comment="Move"   )
    print "l:%f" % l
    print "dL:%f" % dL
    return printSeg

#print a list of segments
def printSegments(li):
    print "  ## printSegments() ##"
    ZTravel = setupData["Z0"] + setupData["TravelHeight"]
    ZWeld   = setupData["Z0"] + setupData["WeldHeight"]
    s  = "; Segments starts\n"
    s += move( z=ZTravel,              speed="Travel", comment="Raise torch" )
    s += move( x=li[0][0], y=li[0][1], speed="Travel", comment="Position start of weld" )
    s += move( z=ZWeld,                speed="Travel", comment="Lower torch" )
    s += "G4 P" + str(int(setupData["PuddleTime"  ]*1000.0)) + " ; Wait to create weld puddle\n"
    for i in range(1, len(li)):
        s += printSegment(li[i-1][0], li[i-1][1], li[i][0], li[i][1])
    return s
    
# The start sequance to initiate the ark & be ready to print
def startSequence():
    print "  ### startSequence() ###"
    startSeq  = "; Initialisation Sequence \nG21    ; Set units to millimeters \nG28    ; Home all axes \nG90    ; Use absolute coordinates \nG92 E0 ; Reset extrusion distance \nM82    ; Use absolute distances for extrusion\n"
    startSeq += "M204 S" + str(setupData["Acceleration"]) + " ; Set the default Acceleration\n" 
    x   = setupData["IgnitCoord"]["x"]
    y   = setupData["IgnitCoord"]["y"]
    zAp = setupData["ApproachHeight"]
    zWe = setupData["WeldHeight"]
    z0  = setupData["Z0"]
    Len = setupData["IgnitCoord"]["len"]
    startSeq += move( x=x-Len, y=y, z=z0+zAp, speed="Travel", comment="Ignition prepare" )
    startSeq += move( x=x,          z=z0,     speed="Travel", comment="Ignition point"   )
    startSeq += move( x=x+Len,      z=z0+zWe, speed="Travel", comment="Go to weld height")
    startSeq += "G4 P" + str(int(setupData["PuddleTime"  ]*1000.0)) + " ; Wait to create weld puddle\n"
    return startSeq

# The actual printing sequence  ######## TO be modified acording to your needs #######
# 
def printSequenceWALL():
    print "  ### printSequence() ###"
    global E
    global setupData
    x         = setupData["IgnitCoord"]["x"] + 20
    y         = setupData["IgnitCoord"]["y"] + 0
    E         = 0.0   # initialise extrusion distance
    printSeq  = "; Welding starts\n"
    # loop for each layers [speed, puddle time]
    for s in [[100, 2.5], [150, 0.5], [175, 0.5], [200, 0.0], [225, 0.0], [250, 0.0], [250, 0.0], [250, 0.0], [250, 0.0], [250, 0.0]]:
        setupData["WeldSpeed" ] = s[0]     # Set the print speed
        setupData["PuddleTime"] = s[1]     # Set the puddle time
        li        = line(x, y, 100,150)    # print a line
        #li        = circle(x, y, 50, 40)   # Print a circle
        printSeq += "; Puddle = " + str(s[1]) + "s \tSpeed = " + str(s[0]) + "mm/min\n"    # Comment for the GCode
        printSeq += printSegments(li)       # generate the GCode
        #y += -10
        #x +=  -5
        setupData["Z0"] += 0.7              # Change layer increment Z position
        printSeq += move( x=0, y=20, z=setupData["Z0"] + setupData["TravelHeight"], speed="Travel", comment="next layer" )  # Move to next layer
    return printSeq

def printSequence():
    print "  ### printSequence() ###"
    global E
    global setupData
    x         = setupData["IgnitCoord"]["x"] + 20
    y         = setupData["IgnitCoord"]["y"] + 0
    E         = 0.0   # initialise extrusion distance
    printSeq  = "; Welding starts\n"
    # loop for each layers [speed, puddle time]
    for s in [[ 60, 2.0, 0]]: #, [ 80, 1.5, 20], [100, 1.5, 40], [100, 1.5, 60]]:
        #setupData["ColdWeldSpeed" ] = s[0]     # Set the print speed
        #setupData["PuddleTime"    ] = s[1]     # Set the puddle time
        print "Set WS to:%f" % setupData["ColdWeldSpeed" ]
        x = 25 + s[2]
        li        = line(x, y, 65, 90)    # print a line
        #li        = circle(x, y, 50, 40)   # Print a circle
        printSeq += "; Puddle = " + str(s[1]) + "s \tSpeed = " + str(s[0]) + "mm/min \tdY = " + str(s[2]) + "\n"    # Comment for the GCode
        printSeq += printSegments(li)       # generate the GCode
        #y += -10
        #x +=  -5
        #setupData["Z0"] += 0.7              # Change layer increment Z position
        #printSeq += move( x=0, y=20, z=setupData["Z0"] + setupData["TravelHeight"], speed="Travel", comment="next layer" )  # Move to next layer
        printSeq += move( z=setupData["Z0"] + setupData["TravelHeight"], speed="Travel", comment="next layer" )  # Move to next layer
    return printSeq

# The stopping sequance to break the ark & return home
def stopSequence():
    print "  ### stopSequence( ) ###"
    stopSeq  = "; Welding Ends\n"
    stopSeq += move( x=lastPoint["x"] + 50.0,      z=lastPoint["z"] + 50.0, speed="Travel", comment="Break Ark")
    stopSeq += "G28 X0  ; home X axis\n"
    return stopSeq

# Save data into a file
def saveData(mydata, fileName):                     # save a string to a given filename
    print "  ### saveData(mydata, fileName) ###"
    if mydata != None:
        print "  #### data to be saved ####"
        try:
            f = open(fileName, "w")
            print "  #### o ####"
            f.write(mydata)
            print "  #### W ####"
        except:
            print "Failed to write file: %s" % fileName
            raise

# Main Code run all the sequences to generate the full gcode file & save it
if __name__ == '__main__':  
    print "##### GCODE Tests Generator #####"
    mydata = startSequence()
    mydata += printSequence()
    mydata += stopSequence()
    #print mydata                                    # Display it on the screen
    saveData(mydata, setupData["GCodeFileName"])     # Save it in the specified file
    
    
    