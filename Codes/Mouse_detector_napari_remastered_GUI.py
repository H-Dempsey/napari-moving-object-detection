# Python code for Background subtraction using OpenCV
import numpy as np
import pandas as pd
import cv2
import napari
from napari_video.napari_video import VideoReaderNP
from glob import glob
# from tqdm import tqdm
import os
import sys
from Zone_drawing_GUI import customise_arena_drawing_GUI, customise_video_recording_GUI
from Video_readers import complete_reader

home = "C:/Users/hazza/Documents/Napari-tracker"
video_paths = glob(os.path.join(home, "Videos", "*"))
video_path  = video_paths[0]
video_name  = os.path.splitext(os.path.basename(video_path))[0]
cap = cv2.VideoCapture(video_path)
ret = False
while ret == False:
    ret, frame = cap.read()
if ret == False:
    print('Could not import background image from video file.')
    sys.exit()
video_height = frame.shape[0]
video_width  = frame.shape[1]
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Create a list of variables, so that shapes can automatically be annotated.
viewer = napari.Viewer()
napari.settings.get_settings().application.playback_fps = round(fps)
# Personalise the native napari image viewer for zone drawing.
viewer = customise_arena_drawing_GUI(viewer, video_height, video_width)
vr = VideoReaderNP(video_paths[0])
viewer.add_image(vr, name='Background video')
viewer.add_shapes(name='Arena', face_color='gray', opacity=0.4)
viewer.layers[-1].mode = 'add_rectangle'
viewer.show(block=True)

# Keep the zone data from the viewer before closing it.
zones = {'Names':[], 'Masks':[]}
zones_indices = [i for i in range(len(viewer.layers)) if 
                 viewer.layers[i].name      != 'Background video' and
                 viewer.layers[i].name[:11] != 'Calibration']
for i in zones_indices:
    zones['Names']  += [viewer.layers[i].name]
    masks_list = viewer.layers[i].to_masks(mask_shape=(video_height, video_width))
    mask = sum(masks_list) # Combine all sub-zones into one zone for each layer.
    mask = np.array(mask*255, dtype=np.uint8)
    zones['Masks'] += [mask]
arena_ind = zones['Names'].index('Arena')

# Make the zones mutually exclusive in the order from first zone to last zone.
ind_no_arena = [i for i in range(len(zones['Names'])) if zones['Names'][i] != 'Arena']
for i in ind_no_arena:
    for j in ind_no_arena:
        if j > i:
            zones['Masks'][i] = cv2.bitwise_and(zones['Masks'][i], cv2.bitwise_not(zones['Masks'][j]))

# Collect the calibration length data from the viewer before closing it.
calibration_names = [layer.name for layer in viewer.layers if 'Calibration' in layer.name]
if len(calibration_names) > 1:
    print('There can only be one layer with "Calibration" in the name.')
    print('This is reserved for the calibration length.')
    sys.exit()
if len(calibration_names) == 1:
    calibration_name = calibration_names[0]
    point1 = viewer.layers[calibration_name].data[0][0]
    point2 = viewer.layers[calibration_name].data[0][1]
    distance_px = np.linalg.norm(point1-point2)
    
    # Find the calibration length in cm from the name (e.g. 'Calibration (20cm)').
    contents_within_brackets = calibration_name.split('(')[1].split(')')[0] # e.g. '20 cm'.
    if 'cm' not in contents_within_brackets and 'CM' not in contents_within_brackets:
        print('The units of the calibration length must be "cm".')
        sys.exit()
    distance_cm = [char for char in contents_within_brackets if char.isdigit()]
    distance_cm = float(''.join(distance_cm))
    
    # Find the conversion factor from pixels to cm.
    px_to_cm = distance_cm / distance_px

viewer_video = napari.Viewer()
viewer_video = customise_video_recording_GUI(viewer_video)
vr_detection = complete_reader(video_path, zones)

from qtpy.QtWidgets import QSlider, QLabel, QPushButton, QLineEdit, QComboBox, QStyledItemDelegate
from qtpy.QtCore import Qt, QRect

default_value = 150
my_label = QLabel(f"Detection threshold: {default_value}")
my_label.setAlignment(Qt.AlignCenter)
my_slider = QSlider(Qt.Horizontal)
my_slider.setMinimum(0)
my_slider.setMaximum(255)
my_slider.setValue(default_value)
my_slider.setSingleStep(1)
def change_threshold(value):
    vr_detection.set_threshold(value)
def update_value(value):
    my_label.setText(f"Detection threshold: {value}")
my_slider.valueChanged[int].connect(change_threshold)
my_slider.valueChanged[int].connect(update_value)

global duration_mins
duration_mins = 5
duration_label = QLabel("Recording duration (mins)")
duration_label.setAlignment(Qt.AlignCenter)
duration_textbox = QLineEdit("5")
duration_textbox.setAlignment(Qt.AlignCenter)
def change_duration(value):
    global duration_mins
    duration_mins = float(value)
duration_textbox.textChanged.connect(change_duration)

add_reset_background_button = QPushButton("Reset background")
def reset_background():
    vr_detection.fgbg = cv2.bgsegm.createBackgroundSubtractorCNT()
add_reset_background_button.clicked.connect(reset_background)

from qtpy.QtCore import QTimer
from napari._qt.qthreading import thread_worker

add_start_recording_button = QPushButton("Start recording")
add_stop_recording_button  = QPushButton("Stop recording")
play_timer = QTimer()

def add_start_recording():
    if add_start_recording_button.text() in ['Start recording', 'Redo recording']:   
        vr_detection.initialise_export_data()
        global start_frame
        start_frame, _, _ = viewer_video.dims.current_step
        global end_frame
        end_frame = start_frame + duration_mins*60*fps
        add_start_recording_button.setText("Stop recording")
        # Pause the video if it is playing.
        if viewer_video.window._qt_viewer.dims.is_playing:
            viewer_video.window._qt_viewer.dims.stop()
        # Start exporting the data.
        vr_detection.start_analysis = True
        @thread_worker
        def next_image_index():
            frame_no, height, width = viewer_video.dims.current_step
            global frame_interval
            return((frame_no+frame_interval, height, width))
        def update_image(step):
            current_frame = step[0]
            if current_frame >= end_frame or current_frame > total_frames:
                add_start_recording_button.setText("Redo recording")
                vr_detection.start_analysis = False
                vr_detection.out.release()
                play_timer.stop()
                update_time()
            else:
                viewer_video.dims.current_step = step
        def play_next_frame():
            worker = next_image_index()
            worker.returned.connect(update_image)
            worker.start()
        play_timer.timeout.connect(play_next_frame)
        play_timer.start(0) # start timer with 0 msec interval to play frames as fast as possible
    elif add_start_recording_button.text() == 'Stop recording':
        add_start_recording_button.setText("Redo recording")
        vr_detection.start_analysis = False
        vr_detection.out.release()
        play_timer.stop()
        update_time()

class CenterDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        painter.setFont(option.font)
        text_rect = QRect(option.rect)
        painter.drawText(text_rect, Qt.AlignCenter, index.data())
        painter.restore()
sample_rate_label = QLabel("Sample rate (frames/sec)")
sample_rate_label.setAlignment(Qt.AlignCenter)
choose_sample_rate_button = QComboBox()
sample_rates = [str(round(fps/i,2)) for i in range(1,10)]
choose_sample_rate_button.addItems(sample_rates)
choose_sample_rate_button.setEditable(True)
choose_sample_rate_button.lineEdit().setAlignment(Qt.AlignCenter)
delegate = CenterDelegate()
choose_sample_rate_button.setItemDelegate(delegate)
def find_frame_interval(i):
    global frame_interval
    frame_interval = i+1
choose_sample_rate_button.currentIndexChanged.connect(find_frame_interval)

add_start_recording_button.clicked.connect(add_start_recording)
viewer_video.window.add_dock_widget((my_label, my_slider, add_reset_background_button, 
    sample_rate_label, choose_sample_rate_button, duration_label, duration_textbox,
    add_start_recording_button), area='right')

blank = 10*' '
add_visualize_button = QPushButton(blank+'Visualize recording (next step)'+blank)
def add_visualize():
    viewer_video.window._qt_window.close()
add_visualize_button.clicked.connect(add_visualize)
viewer_video.window.add_dock_widget((add_visualize_button), area='right')

def update_time():
    position = viewer_video.dims.current_step[0]
    current_time = int(position / fps)
    total_time = int(total_frames / fps)
    current_time_str = f"{current_time//60:02d}:{current_time%60:02d}"
    total_time_str = f"{total_time//60:02d}:{total_time%60:02d}"
    final_label = f"time: {current_time_str} / {total_time_str}"
    spaces = 12*' '
    if len(vr_detection.zone_presence) > 0:
        final_label = 'current zone: '+vr_detection.zone_presence+spaces+final_label
    else:
        final_label = 'current zone: Arena'+spaces+final_label
    if add_start_recording_button.text() == 'Stop recording':
        final_label = 'RECORDING'+spaces+final_label
    viewer_video.text_overlay.text = final_label
    
viewer_video.text_overlay.visible = True
viewer_video.text_overlay.color = np.array([1,1,1,1], dtype=np.float32)
viewer_video.text_overlay.position = 'bottom_right'
viewer_video.dims.events.current_step.connect(update_time)

viewer_video.add_image(vr_detection, name='Detection')
frame_no, height, width = viewer_video.dims.current_step
viewer_video.dims.current_step = (0, height, width)
for i in range(len(viewer.layers)):
    if viewer.layers[i].name != 'Background video':
        viewer_video.add_layer(viewer.layers[i])
viewer.close()
viewer_video.show(block=True)

# ANALYSE DATA.
data_path = os.path.join(home, "Center_point", video_name+'.csv')
data_file   = pd.read_csv(data_path)
data_file.insert(0, 'Frame count', range(len(data_file)))
centre_list = np.array(data_file[['Frame count','X','Y']])
data_file.insert(0, 'Motion ID', 0)
tracks_list = np.array(data_file[['Motion ID','Frame count','X','Y']])
data_file['(X,Y)'] = list(zip(data_file['X'], data_file['Y']))
# Add zone data.
def point_check(value, mask):
    return(1 if zones['Masks'][i][cY][cX] == 255 else 0)
for i in range(len(zones['Names'])):
    data_file[zones['Names'][i]] = data_file['(X,Y)'].apply(point_check, mask=zones['Masks gray'][i])
include_cols = ['Frame count','X','Y'] + zones['Names']
data_file[include_cols].to_csv(data_path, index=False)

# VISUALISE DATA.
        
viewer = napari.Viewer()
viewer.window.main_menu.setVisible(False)
viewer.window._qt_window.showNormal() 

vr = VideoReaderNP(video_path)[start_frame:end_frame]
viewer.add_image(vr, name='Background image')
for i in range(len(zones['Names'])):
    viewer.add_shapes(zones['Napari coords'][i], shape_type=zones['Shapes'][i], 
        name=zones['Names'][i], face_color=zones['Napari colors'][i], opacity=0.2)
vr_motion = VideoReaderNP(motion_path)
viewer.add_image(vr_motion, name='Motion mask', blending='additive')
vr_zones = VideoReaderNP(zones_path)
viewer.add_image(vr_zones, name='Zone labels', blending='additive')
viewer.add_points(centre_list, edge_color='red', face_color='red', size=9, name='Center point')
viewer.add_tracks(tracks_list, blending='opaque', colormap='red')

viewer.show(block=True)
viewer.close()  


