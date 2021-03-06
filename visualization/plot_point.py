from __future__ import print_function

import copy
import numpy as np
import os
import sys

from matplotlib.pyplot import imshow
from PIL import  Image, ImageDraw


def parseBundlerFile(fname):
    f = open(fname,'r')
    count = 0

    for lines in f.readlines():
        count = count + 1
        if count == 1: 
            # this is the title file
            continue
        elif count == 2:
            # second line is num cameras & num keypoints
            tmp = lines.split()
            num_cam = int(tmp[0])
            num_point = int(tmp[1])
            # the reading limit for camera information, each cam is described by 5 lines
            cam_limit = count + 5 * num_cam
            w, h = 3, 5*num_cam
            # camera information output
            CAM = [[0 for x in range(w)] for y in range(h)] 
            w_p,h_p = 3,3*num_point
            p_flag = 0
            PNT = [[0 for x in range(w_p)] for y in range(h_p)]
        elif count <= cam_limit:
            # those 0,1,2 has different meaning for different lines but all lines has 3 numbers
            CAM[count-3][0] = float(lines.split()[0])
            CAM[count-3][1] = float(lines.split()[1])
            CAM[count-3][2] = float(lines.split()[2])
        else:
            p_flag = p_flag + 1
            if p_flag == 1:
                #print count,h
                # 3D position
                for pos in range(0,3):
                    PNT[count-h-3][pos] = float(lines.split()[pos])
            elif p_flag == 2:
                #print count,h
                # RGB color of this keypoint
                for rgb_p in range(0,3):
                    PNT[count-h-3][rgb_p] = float(lines.split()[rgb_p])
            elif p_flag == 3:
                p_flag = 0
                sp=lines.split()
                assert(len(sp)==(4*int(sp[0])+1))
                for view_p in range(4*int(sp[0])):
                    sp[view_p+1]=float(sp[view_p+1])
                PNT[count-h-3]=sp[1:]
    f.close()
    return CAM, PNT

def parseCam(cam):
    # parse the camera into better format
    cam=np.asarray(cam)
    out=[]
    num_cam=int(len(cam)/5)
    for i in range(num_cam):
        this_cam={}
        subcam=cam[i*5:(i+1)*5]
        this_cam["focal_len"]=subcam[0][0]
        this_cam["distort_coeff"]=subcam[0][1:]
        this_cam["R"]=np.matrix(subcam[1:4])
        this_cam["t"]=np.matrix(subcam[4]).T
        out.append(this_cam)
    return out

def parseKeypoints(pnt):
    num_keypoint=int(len(pnt)/3)
    out=[]
    for i in range(num_keypoint):
        this_point={}
        subpnt=pnt[i*3:(i+1)*3]
        this_point["position"]=np.matrix(subpnt[0]).T
        this_point["color"]=np.asarray(subpnt[1])
        # parse the occur of this keypoint in all cameras
        view_list=[]
        for j in range(int(len(subpnt[2])/4)):
            this_cam={}
            subsubpnt=subpnt[2][j*4:(j+1)*4]
            this_cam["camera_index"]=int(subsubpnt[0])
            this_cam["sift_index"]=int(subsubpnt[1])
            this_cam["position"]=np.matrix(subsubpnt[2:]).T
            view_list.append(this_cam)
        this_point["view_list"]=view_list
        
        out.append(this_point)
    return out

def r_func(p, k1, k2):
    # the last z=1 must be removed
    q = np.array([p[0], p[1]])
    norm = float(np.linalg.norm(q))
    return 1.0 + k1*(norm**2) + k2 * (norm**4)

def project(X, R, t, f, k1, k2):
    P = R * X + t
    P = -P/P[2]
    pp = f * r_func(P, k1, k2) * P
    # throw away the Z-axis
    return pp[0:2]
    
def project_simple(X, cam_info):
    return project(X, 
                   cam_info["R"], 
                   cam_info["t"],  
                   cam_info["focal_len"], 
                   cam_info["distort_coeff"][0],
                   cam_info["distort_coeff"][1])

def annotateImage(im, points, color='red'):
    draw = ImageDraw.Draw(im)
    dot_size=3
    imsz=np.asmatrix(im.size)
    for point in points:
        p=copy.deepcopy(point)
        p[1]=-p[1]
        p=np.asmatrix(p)+imsz.T/2
        draw.ellipse((p[0]-dot_size, p[1]-dot_size, 
                      p[0]+dot_size, p[1]+dot_size), 
                      fill = color, outline =color)
    return im

def collectKeypoints(keypoints):
    # a map from camera id to keypoints list
    camid2points={}
    for point in keypoints:
        for appear in point["view_list"]:
            camid = appear["camera_index"]
            pos = appear["position"]
            if camid in camid2points:
                camid2points[camid].append(pos)
            else:
                camid2points[camid]=[pos]
    return camid2points

def isValidCam(cam):
    return cam['focal_len']>0

def egomotion2D(cam, image_id, imsz):
    # calculate the path on 2D image that the car is going to move
    # constants calculation
    projected_y=imsz[1]/2*0.95  # the projected y axis right now
    length=0.1              # the length of show point relative to the camera world center
    
    out=[]
    for i in range(image_id, len(cam)):
        acam=cam[i]
        
        if isValidCam(acam):        
            # kappa is the family of 3D point location that is projected to (0, -projected_y)
            kappa=-np.matrix([0, projected_y/acam["focal_len"],1]).T
            # assume the projected point has the same location relative to the camera world center
            # get the last freedom dim
            P2=length/np.linalg.norm(np.asarray(kappa))
            kappa = kappa*P2
	    #if image_id<2:
	    #    tmp = -acam["R"].T*(acam["t"])
	    #    print(tmp.T)
            X=acam["R"].T*(kappa-acam["t"])
            out.append(project_simple(X, cam[image_id]))
    return out
    
def processImages(paths, bundler_out):
    # annotate the output from the bundler

    # parse the bundler file
    cam, kp=parseBundlerFile(bundler_out)
    cam=parseCam(cam)
    kp=parseKeypoints(kp)
    # collect camera image centric key points
    camid2points=collectKeypoints(kp)
    
    camid=0
    for fp in paths:
        head, tail = os.path.split(fp)
        out_dir=head+"_annotate"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        outpath=os.path.join(out_dir, tail)
        print(outpath)
        #print(fp)
        
        im = Image.open(fp)
        if isValidCam(cam[camid]):
            # plot the keypoints
            im=annotateImage(im, camid2points[camid], color='red')
            # plot the egomotion path
            im=annotateImage(im, egomotion2D(cam, camid, im.size), color='green')
        camid=camid+1

        im.save(outpath)
        im.close()

def verifyGetTestFilenames():
    l=[]
    for j in range(101, 320):
        if j%10 in [1,5,9]:
            l.append("videos/jpg2/00"+str(j)+".jpg")
    return l
        
def verifyPath(cam, i):
    fns=verifyGetTestFilenames()
    fname=fns[i]
    
    print(fname)
    im = Image.open(fname)

    egomotion=egomotion2D(cam, i, (1280,720))
    print(egomotion[0])
    print(egomotion[1])
    
    return annotateImage(im, egomotion, color='green')

def verifyReprojection(cam, kps):   
    for i in range(len(kps)):
        kp=kps[i]["position"]
        atest=kps[i]["view_list"][0]
        print(atest["position"][0], atest["position"][1], end="")

        cam_info=cam[atest["camera_index"]]
        a=project_simple(kp, cam_info)
        print(a[0], a[1])
        
def verifyBundlerImageCorrespondence(cam, kps, i):
    camid2points=collectKeypoints(kps)
    print(len(cam))
    print(i)
    fns=verifyGetTestFilenames()
    fname=fns[i]
    print(fname)
    im = Image.open(fname)
    return annotateImage(im, camid2points[i])

def getAllImages(folder):
    l=[]
    for f in os.listdir(folder):
        if f.lower().endswith("jpg") or f.lower().endswith("png"):
            l.append(os.path.join(folder, f))
    l=sorted(l)
    return l

def getImagesIrr():
    l=[]
    path="../videos/zeros/image%s.jpg"
    for i in range(1215):
        this = path % str(i)
        if os.path.exists(this):
            l.append(this)
    return l

if __name__ == "__main__":
    # called with two arguments: image folder, and bundler output
    processImages(getAllImages(sys.argv[1]), sys.argv[2])    
