#! /usr/bin/env python
################################################
# This is the stand alone version of Mantrack, #
# a tool from the AnimTrack package by J.W.    #
# Jolles. Do not distribute!                   #
################################################

from __future__ import print_function
from six.moves import input

import sys
import os
import cv2
import pandas as pd
import numpy as np
from itertools import cycle

from animlab.utils import *
from animlab.imutils import *
from animlab.mathutils import *

from .__version__ import __version__


class Track_Manual:

    """
    Initializes a manual tracking instance

    Parameters
    ----------
    vidfile : str; no default
        Name of the video file to be manually tracked.
    fileaction : ["replace","newfile","append"]; default = "newfile"
        In the case the trackingfile already exists, either replace the
        file, make a new file with a sequence number, or append to the file.
    ids : list; default = ["1"]
        A list of animal IDs that will be tracked.
    ptypes : list of ["c","f","b"]; default = ["c"]
        One or multiple point locations that need to be tracked, can be "c",
        coordinate in the centre of the animal's body; "f", tip coordinate
        on the front of the animal; "b", bottom coordinate on the back of
        the animal.
    safecount : boolean; default = False
        If an extra careful count should be made for the total number of
        frames. This is necessary when videos likely contain dropped or
        replicated frames, which will otherwise likely result in an error.
    datacrop : boolean; default = False
        If the data should be cropped to the first and last manually tracked
        data point. When start and stopframes are provided datacrop will be
        automatically set to True.
    firstframe : int; default = None
        Frame before which the manually tracked datafile should be cropped.
    lastframe : int; default = None
        Frame after which the manually tracked datafile should be cropped.
    resizeval : float; default = 1
        Value with which the video should be resized. Values larger than 1
        will increase the video size, facilitating careful tracking, while
        those smaller than 1 will decrease video size, facilitating faster
        manual tracking.
    statevar : str; default = None
        Name of a potential state variable that can be coded as 0 and 1.
    customstep : int; default = None
        Custom (forward) step size in frames.

    Returns
    -------
    AnimTrack : class; the AnimTrack class
    """

    def __init__(self, vidfile, fileaction = "newfile", ids = ["1"],
                 ptypes = ["c"], safecount = False, datacrop = False,
                 firstframe = None, lastframe = None, resizeval = 1,
                 statevar = None, customstep = None):

        lineprint("Track Manual "+__version__+" started!\n", label = "AnimTrack")

        check_media(vidfile)

        self.resizeval = resizeval
        self.multiplier = 1./self.resizeval
        self.datacrop = datacrop
        self.fileaction = fileaction

        self.vidfile = vidfile
        self.datafile = name(self.vidfile, ".csv", fileaction)
        self.cap = cv2.VideoCapture(self.vidfile)

        self.fps, self.width, _, self.fcount = get_vid_params(self.cap)
        self.width = int(self.width * self.resizeval)

        if safecount:
            print("Running safe frame count..",end='')
            self.fcount = safe_count(vidfile)

        self.firstframe = firstframe if firstframe is not None else 1
        self.lastframe = lastframe if lastframe is not None else self.fcount

        types = {"c": ("centre", ["x","y"], "red"),
                 "f": ("front", ["fx","fy"], "green"),
                 "b": ("back", ["bx","by"], "blue")}
        self.ids = ids
        self.idpool = cycle(self.ids)
        self.types = [types[x] for x in ptypes]
        self.typepool = cycle(self.types)

        self.ustep = 1 if customstep is None else customstep

        self.columns = sum([i[1] for i in self.types], [])

        self.statevar = statevar
        if statevar is not None:
            self.columns = self.columns + [statevar]

        self.data = create_emptydf(self.columns, self.ids, self.firstframe, self.lastframe)
        if os.path.isfile(self.datafile):
            data = pd.read_csv(self.datafile, header = 0)
            ind = data.loc[(data.frame == data.frame[0])].index[0]
            data.index = list(range(ind, ind+len(data)))
            self.data = data.combine_first(self.data)
            print("Datafile "+os.path.split(self.datafile)[1]+" loaded..")
            self.firstframe = int(self.data.frame[0])
            self.lastframe = int(self.data.frame[len(data)-1])
            missingcols = [col for col in self.columns if col not in list(self.data)]
            missingids = [id for id in self.ids if id not in list(self.data.id)]
            assert len(missingcols)==0,"Column(s) "+", ".join(missingcols)+" not in data, exiting.."
            assert len(missingids)==0,"ID(s) "+", ".join(missingids)+" not in data, exiting.."
        else:
            if not self.datacrop:
                framerange = str(self.firstframe)+":"+str(self.lastframe)
                print("Frame range set to max, "+framerange+"..",end=" ")
            print("Empty datafile '"+os.path.split(self.datafile)[1]+"' created..")
        self.datacopy = self.data.copy()

        self.frameloc = self.firstframe - 1

        self.add = False
        self.mousept = None

        self.ind_start = None
        self.ind_stop = None

        self.drawcoords = False
        self.drawframes = False

        self.uset_id(False)
        self.uset_type(True)

        self.show_windows()
        cv2.setMouseCallback('Video', self.drawpoint)


    def show_windows(self):

        def nothing(x):
            pass

        cv2.namedWindow('Frame position', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Frame position', self.width+200, 30)
        cv2.moveWindow('Frame position', 0, 0)
        framediff = self.lastframe-(self.firstframe+1)
        nsteps, self.stepsize = maxsteps(framediff, 200)
        self.stepsize = max(self.stepsize, 1)
        self.barpos = 0
        self.trackpos = 0
        cv2.createTrackbar('Frame', 'Frame position', self.barpos, nsteps, nothing)

        cv2.namedWindow('Info panel', cv2.WINDOW_AUTOSIZE)
        cv2.imshow("Info panel", self.draw_params)
        cv2.moveWindow('Info panel', 0, 84)

        cv2.namedWindow('Video', cv2.WINDOW_AUTOSIZE)
        cv2.imshow("Video", self.draw_frame)
        cv2.moveWindow('Video', 200, 84)


    def drawpoint(self, event, x, y, flags, param):

        if event == cv2.EVENT_LBUTTONDOWN:
            self.pt = (x,y)
            self.draw()
            self.add = True
        elif event == cv2.EVENT_MOUSEMOVE:
            self.mousept = (x,y)
            self.draw()


    def uset_id(self, reset = True):

        self.id = next(self.idpool)
        if reset:
            self.reset()


    def uset_type(self, reset = True):

        self.type = next(self.typepool)
        self.label = self.type[0]
        self.subcolumns = self.type[1]
        self.col = namedcols(self.type[2])
        if reset:
            self.reset()


    def uset_frameloc(self, change):

        self.frameloc = self.frameloc+change
        if self.frameloc >= self.lastframe-1:
            self.frameloc = self.lastframe-1
        if self.frameloc <= self.firstframe-1:
            self.frameloc = self.firstframe-1

        trackpos = int((self.frameloc-self.firstframe-1)/self.stepsize)
        self.trackpos = 0 if trackpos < 0 else trackpos
        cv2.setTrackbarPos('Frame','Frame position', self.trackpos)
        self.reset()


    def reset(self):

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frameloc)
        _, self.frame = self.cap.read()
        self.frame = imresize(self.frame, self.resizeval)
        self.pt = None
        self.loc = self.data.index[(self.data.frame == self.frameloc+1) & (self.data.id == self.id)][0]
        self.draw()


    def draw(self):

        # Draw frame with points
        self.draw_frame = self.frame.copy()
        pt = pd_to_coords(self.data, self.loc, False, self.subcolumns, self.resizeval)
        if pt is not None:
            cv2.circle(self.draw_frame, pt, 0, self.col, 5)
        if self.pt is not None:
            cv2.circle(self.draw_frame, self.pt, 0, self.col, 10)
            pt = self.pt
        if self.mousept is not None:
            draw_crosshair(self.draw_frame, self.mousept)

        # Draw all points
        if self.drawcoords:
            sub = self.data[self.data.id == self.id].reset_index(drop=True)
            coords, framelist = pd_to_coords(sub, None, True, self.subcolumns, self.resizeval)
            cv2.polylines(self.draw_frame, [coords], False, (0,0,0), 1)
            for i,coord in enumerate(coords):
                coord = tuple(coord[0])
                cv2.circle(self.draw_frame, coord, 0, self.col, 5)
                if self.drawframes:
                    draw_text(self.draw_frame, str(int(framelist[i])), (coord[0]-8,coord[1]), fontsize =  0.3)

        # Draw Params
        self.draw_params = np.zeros((120,200,3), np.uint8)+255
        draw_text(self.draw_params, "Frame:", (0,5), fontsize = 0.5)
        draw_text(self.draw_params, str(self.frameloc+1), (68, 5), fontsize = 0.5)
        draw_text(self.draw_params, "ID:", (0, 25), fontsize =  0.5)
        draw_text(self.draw_params, str(self.id), (68, 25), fontsize =  0.5)
        draw_text(self.draw_params, "Type:", (0, 45), fontsize = 0.5)
        draw_text(self.draw_params, self.label, (68, 45), fontsize =  0.5, col = self.col)
        draw_text(self.draw_params, "Coords                          :", (0, 65), fontsize =  0.5)
        if pt is not None:
            draw_text(self.draw_params, str(pt), (68, 65), fontsize =  0.5)
        if self.statevar is not None:
            state = self.data.loc[self.loc, self.statevar]
            state = str(int(state)) if state == state else "nan"
            draw_text(self.draw_params, "State ("+self.statevar+"): "+state, (0, 85), fontsize =  0.5)


    def savedat(self):

        rowchanges = dfchange(self.datacopy, self.data)[1]
        temp = "change" if rowchanges == 1 else "changes"
        print("User saved..", rowchanges, "row", temp, "recorded..", end= " ")
        if self.datacrop:
            inds = list(self.data.dropna(thresh = 4).index)
            if len(inds)==0:
                print("dataset was emtpy..")
            else:
                if len(inds)<3:
                    inds = [self.firstframe,self.lastframe]
                inds = [inds[0],inds[-1]]
                if self.ind_start != None:
                    inds[0] = self.ind_start
                if self.ind_stop != None:
                    inds[1] = self.ind_stop
                self.data = self.data.loc[inds[0]:inds[-1],]
                print("dataset cropped to frames " + str(min(self.data.frame)) + ":" + str(max(self.data.frame)) + "..", end='')
        if len(self.data) > 2:
            self.data.to_csv(self.datafile, index = False)


    def keypress(self):

        '''
        This function enables the user to use simple keypresses to
        command most of the manual tracking functionality.

        Parameters
        ----------
        The keys q,w,e,r,t,y are used for controlling the video frame position:
        q : go to first frame in video.
        w : go one second back in time
        e : go one frame back in time
        r : go one frame forward in time
        t : go one second forward in time
        y : go to the last video frame
        u : custom step size to go forward in time
        f : opens a textbox for the user to provide a frame number to go to

        Control the type of data tracked:
        i : changes the animal ID to the next ID in the list
        p : changes the point type to the next point type in the list

        Change the animal state:
        x : change state animal is in (0 <> 1). As the default state is NaN,
            make sure to press x twice to set state to 0!

        Visualisations:
        a : show/hide all currently tracked data as connected dots
        z : show/hide the framenumbers for the currently tracked data points
        d : displays the changes made so far

        Storing and exiting:
        n : saves the data in file with predefined name and creates new datafile
        s : saves the data in file with predefined name and exits
        esc : exits the program without saving
        '''

        if self.key == 255:
            return None

        else:

            # save and create new file
            if self.key == ord("n"):
                self.savedat()
                self.data = self.datacopy.copy()
                print("File saved, created additional datafile..")
                self.datafile = name(self.vidfile, ".csv", self.fileaction)
                return True

            # save and exit
            elif self.key == ord("s"):
                self.savedat()
                print("File saved, exiting..")
                return False

            # exit without saving
            elif self.key == 27:
                self.data = self.datacopy.copy()
                print("User exited.. changes discarded..")
                return False

            # display changes
            else:
                if self.key == ord("d"):
                    dfchanges, nchanges = dfchange(self.datacopy, self.data)
                    print("\n", nchanges, "rows changed so far:")
                    print(dfchanges, end='\n')

                # change display
                else:

                    # change id
                    if self.key == ord("i"):
                        self.uset_id()

                    # change point type
                    if self.key == ord("p"):
                        self.uset_type()

                    # Toggle showing all data
                    if self.key == ord("a"):
                        self.drawcoords = not self.drawcoords
                        self.reset()

                    # toggle showing all frame numbers
                    if self.key == ord("z"):
                        self.drawframes = not self.drawframes
                        self.reset()

                    # go to user-provided frame
                    if self.key == ord("f"):
                        self.frameloc = input("Go to frame number:")-1
                        self.reset()

                    # set start and end of data
                    if self.key in [ord("["),ord("]")]:
                        ind = self.data.loc[(self.data.frame == self.frameloc)].index[0]
                        self.datacrop = True
                        if self.key == ord("["):
                            print("Data will be cropped to start at frame",self.frameloc)
                            self.ind_start = ind
                        if self.key == ord("]"):
                            print("Data will be cropped to stop at frame",self.frameloc)
                            self.ind_stop = ind

                    # change state
                    if self.key == ord("x"):
                        state = self.data.loc[self.loc, self.statevar]
                        state = 1 if (state != state or state == 0) else 0
                        self.data.loc[self.loc, self.statevar] = state
                        print("Frame", "%5s" % str(self.frameloc+1), "|", self.id, "| ", end='')
                        print("%10s" % self.statevar, "%1s" % str(int(state)))
                        self.draw()

                    # change frame
                    if self.key in [ord(x) for x in "qwertyu"]:
                        if self.key == ord("q"):
                            change = -self.lastframe
                        if self.key == ord("w"):
                            change = -self.fps
                        if self.key == ord("e"):
                            change = -1
                        if self.key == ord("r"):
                            change = 1
                        if self.key == ord("t"):
                            change = self.fps
                        if self.key == ord("y"):
                            change = self.lastframe
                        if self.key == ord("u"):
                            change = self.ustep
                        self.uset_frameloc(change)

                return True


    def movebar(self):
        barpos = int(cv2.getTrackbarPos('Frame','Frame position'))
        if barpos != self.barpos:
            self.barpos = barpos
            if self.barpos != self.trackpos:
                self.frameloc = int(self.firstframe+(self.barpos * self.stepsize))
                self.reset()


    def track(self):

        while True:

            cv2.imshow("Info panel", self.draw_params)
            cv2.imshow("Video", self.draw_frame)
            height, width = self.draw_frame.shape[:2]
            cv2.resizeWindow('Info panel', 100,500)
            cv2.resizeWindow('Video', int(width*0.5), height)
            self.key = cv2.waitKey(1) & 0xff
            self.movebar()

            if self.keypress() is False:
                break

            if self.add:
                realpt = (int(self.pt[0] * self.multiplier), int(self.pt[1] * self.multiplier))
                self.data.loc[self.loc, self.subcolumns] = realpt
                print("Frame", "%5s" % str(self.frameloc+1), "|", self.id, "| ", end='')
                print("%2s" % " ".join(self.subcolumns), "%4s" % str(self.pt[0]), "%4s" % str(self.pt[1]))
                self.add = False
                self.draw()

        cv2.destroyAllWindows()
        cv2.waitKey(1)
