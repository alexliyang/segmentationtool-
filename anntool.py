
import sys
import cv2
import numpy as np
import os
import glob
#try:
#    from PyQt5 import QtGui, QtCore
#    from PyQt5.QtGui import *
#    from PyQt5.QtCore import *
#    from PyQt5.QtWidgets import *
#    from PyQt5 import uic
#except ImportError:
from PyQt4 import QtGui, QtCore
from PyQt4 import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

#from slic_seg import *    

#from PyQt4 import QtGui, QtCore
#from PyQt4.QtCore import pyqtSlot
#from PyQt4.QtGui import *

COLOR_BG = (0,0,0)
COLOR_FG = (255,255,255)
img_size=(480,640)
iterCount=1

def mask2label(mask):
    r,c = mask.shape[:2]
    label = np.zeros((r,c),np.uint8)
    label[np.where((mask==0)|(mask==2))] = 0
    label[np.where((mask==1)|(mask==3))] = 1
    return label
     

def mask2color(mask):
    r,c = mask.shape[:2]
    color = np.zeros((r,c,3),np.uint8)
    color[np.where((mask==0)|(mask==2))] = COLOR_BG
    color[np.where((mask==1)|(mask==3))] = COLOR_FG
    return color

def mask2SLIColor(mask):
    r,c = mask.shape[:2]
    color = np.zeros((r,c,3),np.uint8)
    color[np.where((mask==0)|(mask==2))] = (0,0,255)
    color[np.where((mask==1)|(mask==3))] = (255,0,0)
    return color

def color2mask(color):
    r,c = color.shape[:2]
    mask = np.zeros((r,c),np.uint8)
    mask[np.where((color==COLOR_BG).all(axis=2))] = 0
    mask[np.where((color==COLOR_FG).all(axis=2))] = 1
    #mask[np.all(color==COLOR_BG, axis=-1)] = 0
    #mask[np.all(color==COLOR_FG, axis=-1)] = 1             

    
    #mask[np.where((color==0).all(axis=-1))] = 0
    #mask[np.where((color==255).all(axis=-1))] = 1
    #print("color 2mask")
    #print(mask.shape)
    #print mask
    return mask

def fliph(img):
    shape = img.shape
    a = np.array(img)
    tmpimg = np.reshape(a[:,::-1],shape)
    cv2.imwrite("f:\\fliph.jpg",tmpimg)
    return tmpimg

def nothing(x):
    pass
	
	
class SegmentTool(QtGui.QMainWindow):

    def __init__(self):
        
        QtGui.QMainWindow.__init__(self)
        #self.a = QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle("GraphCut")
        
        self.img = np.zeros((640,480,3),'uint8')
        self.mask = np.zeros((640,480),'uint8')
        self.oriimg = np.zeros((640,480),'uint8')
        self.radius = 5
        self.foreground = True
        self.background = False
        self.has_label = False
		# Setup file menu
        mainMenu = self.window.menuBar()
        fileMenu = mainMenu.addMenu('&File')

        openButton = QAction(QIcon('exit24.png'), 'Open Image', self.window)
        openButton.setShortcut('Ctrl+O')
        openButton.setStatusTip('Open a file for segmenting.')
        openButton.triggered.connect(self.on_open)
        fileMenu.addAction(openButton)

        saveButton = QAction(QIcon('exit24.png'), 'Save Image', self.window)
        saveButton.setShortcut('Ctrl+S')
        saveButton.setStatusTip('Save file to disk.')
        saveButton.triggered.connect(self.on_save)
        fileMenu.addAction(saveButton)

        closeButton = QAction(QIcon('exit24.png'), 'Exit', self.window)
        closeButton.setShortcut('Ctrl+Q')
        closeButton.setStatusTip('Exit application')
        closeButton.triggered.connect(self.on_close)
        fileMenu.addAction(closeButton)

        # Setup main widget #
        mainWidget = QWidget()
        mainBox = QVBoxLayout()

        # Setup Mode Buttons ##
        buttonLayout = QHBoxLayout()
        self.foregroundButton = QPushButton('Add Foreground Seeds')
        self.foregroundButton.clicked.connect(self.on_foreground)
        self.foregroundButton.setStyleSheet("background-color: gray")

        self.backGroundButton = QPushButton('Add Background Seeds')
        self.backGroundButton.clicked.connect(self.on_background)
        self.backGroundButton.setStyleSheet("background-color: white")

        clearButton = QPushButton('Clear All Seeds')
        clearButton.clicked.connect(self.on_clear)

        segmentButton = QPushButton('Segment Image')
        segmentButton.clicked.connect(self.on_segment)
        
        self.sliderBrush = QSlider()
        self.sliderBrush.setMinimumSize(QtCore.QSize(170, 0))
        self.sliderBrush.setMaximum(100)
        self.sliderBrush.setValue(5)
        self.sliderBrush.setOrientation(QtCore.Qt.Horizontal)
        #self.sliderBrush.setObjectName(_fromUtf8("sliderBrush"))
        self.sliderBrush.valueChanged.connect(self.brushSelect)
		
        self.brushLabel = QLabel('Brush size:  5')
		
        buttonLayout.addWidget(self.foregroundButton)
        buttonLayout.addWidget(self.backGroundButton)
        buttonLayout.addWidget(clearButton)
        buttonLayout.addWidget(segmentButton)
        buttonLayout.addWidget(self.brushLabel)
        buttonLayout.addWidget(self.sliderBrush)
		
        buttonLayout.addStretch()
        ##

        mainBox.addLayout(buttonLayout)

        # Setup Image Area ##
        imageLayout = QHBoxLayout()

        self.seedLabel = QLabel()
        self.seedLabel.setPixmap(QPixmap.fromImage(
            self.get_qimage(self.img)))
        self.seedLabel.mousePressEvent = self.mouse_down
        self.seedLabel.mouseMoveEvent = self.mouse_drag

        self.segmentLabel = QLabel()
        self.segmentLabel.setPixmap(QPixmap.fromImage(
            self.get_qimage(mask2color(self.mask))))

        self.allFiles = QtGui.QListWidget(self)
        self.allFiles.resize(180,640)
        self.allFiles.setFixedWidth(180)
        self.allimgs = []
        self.allFiles.itemClicked.connect(self.itemClick)
        
        imageLayout.addWidget(self.allFiles)
        imageLayout.addWidget(self.seedLabel)
        imageLayout.addWidget(self.segmentLabel)
        imageLayout.addStretch()
        mainBox.addLayout(imageLayout)
        ##
        mainBox.addStretch()
        mainWidget.setLayout(mainBox)
        

        self.window.installEventFilter(self)
        
        #
        self.window.setCentralWidget(mainWidget)

        self.filepath = ''
        self.filename = ''

    def __init_mask(self, mask):
        x,y = mask.shape
        mask[:] = cv2.GC_PR_BGD
        x = int(x/2)
        y = int(y/2)
        mask[(x-50):(x+50),(y-50):(y+50)] = cv2.GC_PR_FGD
        print("init mask shpae")
        print(mask.shape)

    def updatesegmentLabelImg(self):
        self.segmentLabel.setPixmap(QPixmap.fromImage(
            self.get_qimage( mask2color(self.mask))))  #


    def updateseedLabelImg(self):
        
        color = mask2color(self.mask)
        #alpha = 0.5 if self.draw_color==0 else (1 if self.draw_color==1 else 0)
        alpha = 0.7 
        show_img = (self.img*alpha + color*(1-alpha)).astype('uint8')
        self.seedLabel.setPixmap(QPixmap.fromImage(
            self.get_qimage(show_img)))

		
		
    def run(self):
        self.window.show()
        #sys.exit(self.a.exec_())
        

    @staticmethod
    def get_qimage(cvimage):
        height, width, bytes_per_pix = cvimage.shape
        bytes_per_line = width * bytes_per_pix;
        cv2.cvtColor(cvimage, cv2.COLOR_BGR2RGB, cvimage)
        return QImage(cvimage.data, width, height, QImage.Format_RGB888)

    @pyqtSlot()
    def on_foreground(self):
        self.foreground = True
        self.background = False
        self.foregroundButton.setStyleSheet("background-color: gray")
        self.backGroundButton.setStyleSheet("background-color: white")

    @pyqtSlot()
    def on_background(self):
        self.foreground = False
        self.background = True
        self.foregroundButton.setStyleSheet("background-color: white")
        self.backGroundButton.setStyleSheet("background-color: gray")

    @pyqtSlot()
    def on_clear(self):
        self.img = np.copy(self.oriimg)	
        self.mask = np.zeros(self.img.shape[:2],'uint8')
        self.__init_mask(self.mask)
        self.updatesegmentLabelImg()
        self.updateseedLabelImg()

    @pyqtSlot()
    def on_segment(self):
        self.bgdModel = np.zeros((1,65),np.float64)
        self.fgdModel = np.zeros((1,65),np.float64)
        cv2.grabCut(self.oriimg, self.mask, None, self.bgdModel, self.fgdModel, iterCount, cv2.GC_INIT_WITH_MASK)
        self.img = np.copy(self.oriimg)
        #self.mask = mask2label(self.mask)
        #mask = color2mask(SLIC_Seg(self.oriimg,mask2SLIColor(self.mask)))
        #self.img = np.copy(self.oriimg)
        #self.mask = mask
        self.updatesegmentLabelImg()
        self.updateseedLabelImg()

    @pyqtSlot()
    def on_open(self):
        file_name = QFileDialog.getOpenFileName(self.window, 'Open Photo', 'f:\\', 'images(*.png *.jpg *.jpeg)')
        #file_name = QFileDialog.getOpenFileName()
        self.has_label = False 
        if file_name is not None and file_name != "":
            print(file_name)
            #self.filename = str(os.path.basename(str(file_name)))
            #self.filepath = file_name[:(len(str(file_name))-len(self.filename))]
            self.filepath,self.filename = os.path.split(str(file_name))
            #print(self.filepath + "           " + self.filename)
            self.oriimg = cv2.resize(cv2.imread(str(file_name)),(480,640),interpolation=cv2.INTER_NEAREST)
            self.img = np.copy(self.oriimg)
            self.mask = np.zeros(self.img.shape[:2],'uint8')
            #print("mask shape")
            #print(self.mask.shape)
            #print("img shape")
            #print(self.img.shape)
            file_split = self.filename.split(".")
            back_step = len(file_split[len(file_split)-1])+1 # +1 including "."
            label_file = self.filepath + "/label/" + self.filename[:-back_step]+".png"
            print label_file
            label_file = os.path.normpath(label_file)
            if not os.path.exists(label_file) :
                self.__init_mask(self.mask)
                self.bgdModel = np.zeros((1,65),np.float64)
                self.fgdModel = np.zeros((1,65),np.float64)
                cv2.grabCut(self.img, self.mask, None, self.bgdModel, self.fgdModel, iterCount, cv2.GC_INIT_WITH_MASK)
                #self.mask = mask2label(self.mask)
            else:
                self.mask = cv2.resize(cv2.imread(str(label_file),-1),(480,640),interpolation=cv2.INTER_NEAREST)
            self.updatesegmentLabelImg()
            self.updateseedLabelImg()
            #here update a file list
            self.allimgs = []
            self.allFiles.clear()
            file_suf = "/*." + file_split[len(file_split)-1]
            self.allimgs = glob.glob(os.path.normpath(self.filepath) + file_suf)
            print (len(self.allimgs))
            for imgTmp in self.allimgs:
                self.allFiles.addItem(os.path.basename(imgTmp))
            cur_id = self.allimgs.index(os.path.normpath(str(file_name)))
            self.allFiles.setCurrentRow(cur_id)

    @pyqtSlot()
    def on_save(self):
        #f = QFileDialog.getSaveFileName()
        print 'Saving filename'
        #file_name = QFileDialog.getSaveFileName(self.window, 'Save File', '', 'images(*.png)')
        print (self.filename)
        file_split = self.filename.split(".")
        back_step = len(file_split[len(file_split)-1])+1
        
        
        file_name = file_split[0]#self.filename[:-4]
        print file_name
        save_path = self.filepath + "/label"
        save_path = os.path.normpath(save_path)
        if not os.path.exists(save_path) :
            os.makedirs(save_path)
        jpg_path = self.filepath + "/jpg"
        jpg_path = os.path.normpath(jpg_path)
        if not os.path.exists(jpg_path) :
            os.makedirs(jpg_path)
        print (file_name) 
        if file_name is not None and file_name != "":
            #file_name = self.filename[:-4] 

            file_name1 = str(file_name) + ".png"
            file_namec = str(file_name)+"_c.png"
            save_img1 = os.path.join(save_path,file_name1)
            save_imgc = os.path.join(save_path,file_namec)
            print save_img1
            print save_imgc
            self.mask = mask2label(self.mask)
            cv2.imwrite(save_img1, self.mask)
            jpg_name = str(file_name) + ".jpg"
            save_jpg = os.path.join(jpg_path,jpg_name)
            cv2.imwrite(save_jpg, self.oriimg)
            if os.path.exists(os.path.join(self.filepath,self.filename)):
                os.remove(os.path.join(self.filepath,self.filename))
            #cv2.imwrite(save_imgc, mask2color(self.mask))
            QMessageBox.information(self,"SegmentTool","Saving Finish",QMessageBox.Yes)  #| QMessageBox.No

    @pyqtSlot()
    def on_close(self):
        print 'Closing'
        self.window.close()

    def mouse_down(self, event):
        x, y = event.pos().x() , event.pos().y()
        if(self.foreground == True and self.mask.size>0 and self.img.size>0):
            cv2.circle(self.img, (x,y), self.radius, (COLOR_FG if self.foreground else tuple([k/3 for k in COLOR_FG])), -1)
            cv2.circle(self.mask, (x,y), self.radius, (cv2.GC_FGD if self.foreground else cv2.GC_PR_FGD), -1)
            
        if(self.background == True and self.mask.size>0 and self.img.size>0):
            #x, y = event.pos().x() , event.pos().y()
            cv2.circle(self.img, (x,y), self.radius, (COLOR_BG if self.background else tuple([k/3 for k in COLOR_BG])), -1)
            cv2.circle(self.mask, (x,y), self.radius, (cv2.GC_BGD if self.background else cv2.GC_PR_BGD), -1)
        #else:
        #    pass
        self.updatesegmentLabelImg()
        self.updateseedLabelImg()			
        #pass


    def mouse_drag(self, event):
        x, y = event.pos().x() , event.pos().y()
        if(self.foreground == True and self.mask.size>0 and self.img.size>0):
            cv2.circle(self.img, (x,y), self.radius, (COLOR_FG if self.foreground else tuple([k/3 for k in COLOR_FG])), -1)
            cv2.circle(self.mask, (x,y), self.radius, (cv2.GC_FGD if self.foreground else cv2.GC_PR_FGD), -1)
            
        if(self.background == True and self.mask.size>0 and self.img.size>0):
            #x, y = event.pos().x() , event.pos().y()
            cv2.circle(self.img, (x,y), self.radius, (COLOR_BG if self.background else tuple([k/3 for k in COLOR_BG])), -1)
            cv2.circle(self.mask, (x,y), self.radius, (cv2.GC_BGD if self.background else cv2.GC_PR_BGD), -1)
        #else:
        #    pass
        self.updatesegmentLabelImg()
        self.updateseedLabelImg()			
        

    def eventFilter(self,source,event):
          
        if(event.type() == QEvent.KeyPress):
            print('key press')
            self.keyPressEvent(event)
        #if(event.type() == QEvent.MouseMove):
        #    print('mouse move')
        return QWidget.eventFilter(self, source, event)

    def keyPressEvent(self, event):
        print('keyPress')
        if (event.key() == QtCore.Qt.Key_Control):    
            print("key ctrl")
        if(event.key()== QtCore.Qt.Key_Shift):
            print("key shift")
        if(event.key()== QtCore.Qt.Key_A):
            print("key A")
            self.bgdModel = np.zeros((1,65),np.float64)
            self.fgdModel = np.zeros((1,65),np.float64)
            cv2.grabCut(self.oriimg, self.mask, None, self.bgdModel, self.fgdModel, iterCount, cv2.GC_INIT_WITH_MASK)
            self.img = np.copy(self.oriimg)
            self.updatesegmentLabelImg()
            self.updateseedLabelImg()

        if(event.key()== QtCore.Qt.Key_S):
            print("key S")
            self.on_save()
        if(event.key()== QtCore.Qt.Key_Escape):
            print("key ESC")
            self.on_close()
        if(event.key()== QtCore.Qt.Key_Enter):
            print("key Enter")
        if(event.key()== QtCore.Qt.Key_Return):
            print("key return")

		
    def brushSelect(self):
        self.radius = int(self.sliderBrush.value())
        self.brushLabel.setText('Brush size:' + str(self.radius))

    def itemClick(self): 
        tmp = self.allFiles.currentItem().text()  
        index = self.allFiles.currentRow()
        file_name = self.allimgs[index]
        #imgOri = cv.imread(str(tmp),1)      
        self.has_label = False 
        if file_name is not None and file_name != "":
            print(file_name)
            #self.filename = str(os.path.basename(str(file_name)))
            #self.filepath = file_name[:(len(str(file_name))-len(self.filename))]
            self.filepath,self.filename = os.path.split(str(file_name))
            #print(self.filepath + "           " + self.filename)
            self.oriimg = cv2.resize(cv2.imread(str(file_name)),(480,640),interpolation=cv2.INTER_NEAREST)
            self.img = np.copy(self.oriimg)
            self.mask = np.zeros(self.img.shape[:2],'uint8')
            #print("mask shape")
            #print(self.mask.shape)
            #print("img shape")
            #print(self.img.shape)
            label_file = self.filepath + "/label/" + self.filename[:-4]+".png"
            label_file = os.path.normpath(label_file)
            if not os.path.exists(label_file) :
                self.__init_mask(self.mask)
                self.bgdModel = np.zeros((1,65),np.float64)
                self.fgdModel = np.zeros((1,65),np.float64)
                cv2.grabCut(self.img, self.mask, None, self.bgdModel, self.fgdModel, iterCount, cv2.GC_INIT_WITH_MASK)
            else:
                self.mask = cv2.resize(cv2.imread(str(label_file),-1),(480,640),interpolation=cv2.INTER_NEAREST)
            self.updatesegmentLabelImg()
            self.updateseedLabelImg()
        
				
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    tool = SegmentTool()
    tool.run()
    sys.exit(app.exec_())
