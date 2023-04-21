from qtpy.QtWidgets import QPushButton, QListWidget, QSlider, QLabel
from qtpy.QtCore import Qt
import matplotlib.pyplot as plt
from glob import glob
import os

def customise_arena_drawing_GUI(viewer, video_height, video_width):

    viewer.window.main_menu.setVisible(False)
    viewer.window._qt_window.showNormal()
    
    for num in [0,1,2,4]:
        viewer.window._qt_viewer.layerButtons.layout().itemAt(num).widget().hide()
    for num in [0,1,2,3,4,5]:
        viewer.window._qt_viewer.viewerButtons.layout().itemAt(num).widget().hide()
        
    global num_zones
    num_zones = 0
    add_zone_button = QPushButton('Add zone')
    def add_zone():
        global num_zones
        color = list(plt.cm.tab20(num_zones*0.1))
        viewer.add_shapes(name='(Double click here)', face_color=color, opacity=0.4)
        viewer.layers[-1].mode = 'add_rectangle'
        num_zones += 1
    add_zone_button.clicked.connect(add_zone)
    
    delete_zone_button = QPushButton('Delete zone')
    def delete_zone():
        viewer.layers.remove_selected()
    delete_zone_button.clicked.connect(delete_zone)
    
    add_calibration_button = QPushButton('Add calibration')
    def add_calibration():
        viewer.add_shapes(name='Calibration (20cm)', edge_color='yellow', edge_width=2, 
                          shape_type='line', opacity=1)
        viewer.layers[-1].mode = 'add_line'
    add_calibration_button.clicked.connect(add_calibration)
    
    blank = 10*' '
    add_record_button = QPushButton(blank+'Record video (next step)'+blank)
    def add_record():
        viewer.window._qt_window.close()
    add_record_button.clicked.connect(add_record)
    
    def keep_aspect_ratio():
        for i in range(len(viewer.layers)):
            viewer.layers[i]._fixed_aspect = False
    # viewer.events.layers_change will become depreciated in 0.5.0.
    import warnings
    warnings.simplefilter(action='ignore', category=FutureWarning)
    try: 
        viewer.events.layers_change.connect(keep_aspect_ratio)
    except:
        pass
    
    zones_warning = QLabel("If zones are overlapping, make sure the larger ones\n"+
                           "are drawn first and the smaller ones are drawn last.\n"+
                           "All zones will be made mutually exclusive.")
    zones_warning.setAlignment(Qt.AlignCenter)
    viewer.window.add_dock_widget((zones_warning), area='left')
    viewer.window.add_dock_widget((add_zone_button, delete_zone_button, 
                                   add_calibration_button), area='right')
    viewer.window.add_dock_widget((add_record_button), area='right')
    viewer.events.help.block()
    viewer.events.status.block()

    return(viewer)

def customise_video_recording_GUI(viewer):
    
    viewer.window.main_menu.setVisible(False)
    viewer.window._qt_window.showNormal()
    
    for num in [0,1,2,4]:
        viewer.window._qt_viewer.layerButtons.layout().itemAt(num).widget().hide()
    for num in [0,1,2,3,4,5]:
        viewer.window._qt_viewer.viewerButtons.layout().itemAt(num).widget().hide()
    
    viewer.events.help.block()
    viewer.events.status.block()

    return(viewer)
