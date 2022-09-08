# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ODKConnector
                                 A QGIS plugin
 This plugIn connect you to your ODK instance and then pulls forms for you to use into QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-08-20
        git sha              : $Format:%H$
        copyright            : (C) 2022 by DDDev
        email                : demeveng@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog, QTableWidgetItem
from qgis.core import QgsFields, QgsField, QgsFeature, QgsProject, QgsVectorFileWriter, QgsGeometry, QgsPointXY, QgsWkbTypes, QgsVectorLayer, QgsVectorDataProvider

# Initialize Qt resources from file resources.py
import requests as rq
import csv

from .resources import *
# Import the code for the dialog
from .odkConnector_dialog import ODKConnectorDialog
import os.path


class ODKConnector:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ODKConnector_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ODK Connector')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # project global variables
        self.keysList = list()
        self.dataList = list()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ODKConnector', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/odkConnector/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&ODK Connector'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ODKConnectorDialog()
            self.dlg.connect.clicked.connect(self.connectionStatus)
            self.dlg.previewData.clicked.connect(self.previewJsonData)
            self.dlg.browsOutput.clicked.connect(self.fileBrowser)
            self.dlg.singleGeo.toggled.connect(self.geometryState)
            self.dlg.noGeometry.toggled.connect(self.noGeometryState)
            self.dlg.addPcodes.toggled.connect(self.enablePcodes)
            self.dlg.closeMain.clicked.connect(self.closeWindow)
            self.dlg.runProcess.clicked.connect(self.process)
            self.dlg.updateLayer.toggled.connect(self.layerUpdateState)
            #self.dlg.tabWidget.currentChanged(0).connect(self.changeButtonText)
            #self.dlg.tabWidget.currentChanged(1).connect(self.changeButtonText)
            #QMessageBox.information(self.dlg, "Message", "This is an ODK2QGIS Connector")

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

#======================FUNCTIONS===========================================
    #Slot functions
    def connectionStatus(self):
        global data
        self.dlg.connectionResult.clear()
        try:
            #url = ""
            url = self.dlg.url.text()
            #user=""
            user = self.dlg.userName.text()
            #pwd = ""
            pwd = self.dlg.password.text()
            data = rq.get(url, auth = (user,pwd))
            #print(data)
            if data.status_code == 200:
                self.dlg.connectionResult.setText('<span style=\" color: #006400;\">%s</span>' % ("Connection sucessful with code : "+ str(data.status_code)))
            else:
                self.dlg.connectionResult.setText('<span style=\" color: #ff0000;\">%s</span>' % ("Connection failed with code : "+ str(data.status_code)))
        except Exception as e:
            self.dlg.connectionResult.setText('<span style=\" color: #ff0000;\">%s</span>' % ("Connection faild with error message : "+ str(e)))

    def previewJsonData(self):
        #global keysList #list containing the keys (column names of the data)
        #global dataList #List containing the row data in form of lists
        self.dataList = list() #contains the data in a list
        # clear all widgets
        self.dlg.jsonText.clear()
        self.dlg.dataTable.clear()
        self.dlg.tableSize.clear()
        self.dlg.latitude.clear()
        self.dlg.longitude.clear()
        self.dlg.geometry.clear()
        self.dlg.adminColumn.clear()
        # function to preview the data in the Qplaintextwidget and the qtablewiget
        jsonData = data.json() #load the data into a json data structure
        self.keysList = list() # get the keys of the data
        # get all possible keys in the json file. the looping ensures that all fields are captured when the length of the dicts are not equal
        for i in jsonData:
            self.dlg.jsonText.appendPlainText("----" + str(list(i.values())) + "\n")
            for j in i.keys():
                if j in self.keysList:
                    continue
                else:
                    self.keysList.append(j)

        self.dlg.jsonText.appendPlainText(str(self.keysList) + "\n") # display the columns names in the QPlaintextwiget
        #loop through the data and display the rows in the QPlaintextwidget
        for i in jsonData:
            self.dlg.jsonText.appendPlainText(str(list(i.values())) + "\n") # display the data in the QPlaintextwiget
            li = list() # list to contain row data making sure they have the same number of inputs as the number of comlumns to avoid data mismatch in the output file

            for j in self.keysList:
                if j in i.keys():
                    li.append(i[j])
                else:
                    li.append("")
            self.dataList.append(li)

        #populate the QTablewiget
        for i in range(0, len(self.keysList)): # create columns objects in the table before populating them with values
            self.dlg.dataTable.insertColumn(i)

        self.dlg.dataTable.setHorizontalHeaderLabels(self.keysList) #display the columns
        self.dlg.dataTable.setRowCount(len(self.dataList)) #set the length of the table rows
        row = 0 #row number
        for d in jsonData:# loop through the json data and populate the qtablewiget
            column = 0
            rowKeys = d.keys()
            for key in self.keysList:
                if key in rowKeys:
                    self.dlg.dataTable.setItem(row,column, QTableWidgetItem(str(d[key])))
                    column += 1
                else:
                    self.dlg.dataTable.setItem(row,column, QTableWidgetItem(""))
                    column += 1
            row += 1
        #Populate qplaintext and qdropdown wigets with data
        self.dlg.tableSize.setText('<span style=\" color: #006400;\">%s</span>' %("Table size : " + str(len(self.dataList)) + " Rows x " + str(len(self.keysList)) + " Columns"))
        self.dlg.latitude.addItems(self.keysList)
        self.dlg.longitude.addItems(self.keysList)
        self.dlg.geometry.addItems(self.keysList)
        self.dlg.adminColumn.addItems(self.keysList)

    def fileBrowser(self): #brows and create the output file data in .gpkg and .shp
        fname, format = QFileDialog.getSaveFileName(self.dlg, 'Save file', 'c:\\',"GPKG (*.gpkg);;ESRI Shapefile (*.shp);;comma-seperated values (*.csv)")
        if self.dlg.noGeometry.isChecked():
            fname = os.path.join(os.path.dirname(fname),os.path.basename(fname).split(".")[0] + ".csv")
        self.dlg.outputFile.clear()
        self.dlg.outputFile.setText(fname)
        #self.dlg.jsonText.appendPlainText(format)
    def geometryState(self):
        #toggle the geometry combobox state
        if self.dlg.singleGeo.isChecked():
            self.dlg.geometry.setEnabled(True)
            self.dlg.latitude.setEnabled(False)
            self.dlg.longitude.setEnabled(False)
        else:
            self.dlg.geometry.setEnabled(False)
            self.dlg.latitude.setEnabled(True)
            self.dlg.longitude.setEnabled(True)
    
    def noGeometryState(self):
        #toggle the no-geometry combobox state
        if self.dlg.noGeometry.isChecked():
            self.dlg.singleGeo.setEnabled(False)
            self.dlg.geometry.setEnabled(False)
            self.dlg.latitude.setEnabled(False)
            self.dlg.longitude.setEnabled(False)
            self.dlg.updateLayer.setEnabled(False)
        else:
            self.dlg.updateLayer.setEnabled(True)
            self.dlg.singleGeo.setEnabled(True)
            self.geometryState()
    
    def enablePcodes(self):
        #toggle the pcodes combobox state
        if self.dlg.addPcodes.isChecked():
            self.dlg.adminColumn.setEnabled(True)
            self.dlg.adminLevel.setEnabled(True)
        else:
            self.dlg.adminColumn.setEnabled(False)
            self.dlg.adminLevel.setEnabled(False)
    
    def splitLatLongAltPrec(self):
        geometryColumn = self.dlg.geometry.currentText()

    def createFeatureClass(self, filePath, format, crs):
        # define fields for feature attributes. A QgsFields object is needed
        featureFields = QgsFields()
        # populate the fields with the column names stored in Keylist
        for field in self.keysList:
            self.dlg.jsonText.appendPlainText(field)
            featureFields.append(QgsField(field.replace("/","_"), QVariant.String))
        
        crs = crs #QgsProject.instance().crs()
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        if format == "shp":
            save_options.driverName = "ESRI Shapefile" #output format of featureclass ex: "ESRI Shapefile"
        elif format == "gpkg":
            save_options.driverName = "GPKG"
        save_options.fileEncoding = "UTF-8"

        writer = QgsVectorFileWriter.create(filePath, featureFields, QgsWkbTypes.Point, crs, transform_context, save_options)

        if writer.hasError() != QgsVectorFileWriter.NoError:
            self.dlg.processingMsg.setText('<span style=\" color: #ff0000;\">%s</span>' % ("Error when creating file: ",  writer.errorMessage()))

        # add a feature
        fet = QgsFeature()

        for row in self.dataList:
            i = 0
            row2 = row.copy()
            if self.dlg.singleGeo.isChecked():# do when a single column geometry is checked
                geomCol = self.dlg.geometry.currentText()
                index = self.keysList.index(geomCol)
                if type(row[index]) == type(list()):
                    fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[index][1]),float(row[index][0]))))
                else:
                    fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[index].split(" ")[1]),float(row[index].split(" ")[0]))))
            else: # do when lon and lat columns are selected.
                lat = self.dlg.latitude.currentText()
                long = self.dlg.longitude.currentText()
                fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(lat),float(long))))
            
            for d in row2:
                if type(d) == type(list()):
                    row2[i] = "[]"
                i += 1

            fet.setAttributes(row2)
            writer.addFeature(fet)

        # delete the writer to flush features to disk
        del writer
    
    def createCSV(self, path, filename):
        file = os.path.join(os.path.dirname(path), filename + ".csv")
        responsejson = data.json()
        with open(file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.keysList)

            writer.writeheader()
            for row in responsejson:
                writer.writerow(row)
        self.dlg.outputFile.clear()
        self.dlg.outputFile.setText(file)

    def addPcodesColumn(self):
        pass

    def closeWindow(self):
        self.dlg.close() # Close the mainWindow. The close() function is an inbuilt function in pyqt
    
    def layerUpdateState(self):
        #toggle the no-geometry combobox state
        if self.dlg.updateLayer.isChecked():
            # self.dlg.outputFile.setEnabled(False)
            # self.dlg.browsOutput.setEnabled(False)
            # self.dlg.addPcodes.setEnabled(False)
            # self.dlg.noGeometry.setEnabled(False)
            self.dlg.layerToUpdate.setEnabled(True)
        else:
            # self.dlg.outputFile.setEnabled(True)
            # self.dlg.browsOutput.setEnabled(True)
            # self.dlg.addPcodes.setEnabled(True)
            # self.dlg.noGeometry.setEnabled(True)
            self.dlg.layerToUpdate.setEnabled(False)

    def updateLayer(self):
        # get the selected layer to be updated
        self.dlg.jsonText.appendPlainText("Update started")
        selectedLayer = self.dlg.layerToUpdate.currentLayer()
        self.dlg.jsonText.appendPlainText("Layer Selected")
        caps = selectedLayer.dataProvider().capabilities() # get the supported capabilities of the dataProvider (e.g ESRI Shapefile)
        # delete the elements in the layer
        if caps & QgsVectorDataProvider.DeleteFeatures:
            self.dlg.jsonText.appendPlainText("Delete capabilities supported")
            #check is layer is not in edit mode
            if not selectedLayer.isEditable():
                selectedLayer.startEditing() # start layer editing
                for feat in selectedLayer.getFeatures():
                    selectedLayer.deleteFeature(feat.id())
                    self.dlg.jsonText.appendPlainText(str(feat.id()))
                selectedLayer.commitChanges() # save edits
            else:
                for feat in selectedLayer.getFeatures():
                    selectedLayer.deleteFeature(feat.id())
                    self.dlg.jsonText.appendPlainText(str(feat.id()))
        self.dlg.jsonText.appendPlainText("Data deleted")
        # append new elements into the layer
        if caps & QgsVectorDataProvider.AddFeatures:
            fields = selectedLayer.fields()
            # feature object
            feat = QgsFeature(fields)
            for row in self.dataList:
                i = 0
                row2 = row.copy()
                if self.dlg.singleGeo.isChecked():# do when a single column geometry is checked
                    geomCol = self.dlg.geometry.currentText()
                    index = self.keysList.index(geomCol)
                    if type(row[index]) == type(list()):
                        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[index][1]),float(row[index][0]))))
                    else:
                        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[index].split(" ")[1]),float(row[index].split(" ")[0]))))
                else: # do when lon and lat columns are selected.
                    lat = self.dlg.latitude.currentText()
                    long = self.dlg.longitude.currentText()
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(lat),float(long))))
                
                for d in row2:
                    if type(d) == type(list()):
                        row2[i] = "[]"
                    i += 1

                feat.setAttributes(row2)
                selectedLayer.dataProvider().addFeature(feat)
            
        selectedLayer.commitChanges()
        self.dlg.jsonText.appendPlainText("Data Updated")
    
    def changeButtonText(self):
        if self.dlg.tabWidget.currentIndex() == 0:
            self.dlg.runProcess.setText("Run")
        else:
            self.dlg.runProcess.setText("Update Layer")

    def process(self):
        try:
            self.dlg.progressBar.setValue(0)
            crs = self.dlg.csr.crs()
            self.dlg.processingMsg.setText("Processing...")
            self.dlg.progressBar.setValue(10)
            if self.dlg.updateLayer.isChecked():
                pass
            else:
                outFile = self.dlg.outputFile.text() #output file path
                fileName = os.path.basename(outFile).split(".")[0]#output path basename
                format = os.path.basename(outFile).split(".")[1]
                self.dlg.progressBar.setValue(20)

            if self.dlg.noGeometry.isChecked():#if no geometry is required or if file has no geometry
                self.createCSV(outFile, fileName)
                self.dlg.progressBar.setValue(80)

            elif self.dlg.updateLayer.isChecked():
                self.updateLayer()

            else:
                self.createFeatureClass(outFile, format, crs)
                self.dlg.progressBar.setValue(80)

            if self.dlg.loadData.isChecked() and self.dlg.updateLayer.isChecked() == False:
                vlayer = QgsVectorLayer(outFile, fileName, "ogr") #QGIS vector data loader
                QgsProject.instance().addMapLayer(vlayer) # adding the vector data into QGIS
                self.dlg.progressBar.setValue(90)
            self.dlg.processingMsg.setText('<span style=\" color: #006400;\">%s</span>' % ("Done!"))
            self.dlg.progressBar.setValue(100)

        except Exception as e:
            self.dlg.processingMsg.setText('<span style=\" color: #ff0000;\">%s</span>' % str(e))
            self.dlg.progressBar.setValue(0)