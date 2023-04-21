from napari_video.napari_video import VideoReaderNP
import pandas as pd
import cv2
import os

class complete_reader(VideoReaderNP):
    
    def __init__(self, filename: str, zones, remove_leading_singleton: bool = True):
        self.fgbg = cv2.bgsegm.createBackgroundSubtractorCNT()
        self.threshold = 150
        self.last_known_cX = 0
        self.last_known_cY = 0
        self.zones = zones
        self.arena_ind = zones['Names'].index('Arena')
        self.ind_no_arena = [i for i in range(len(zones['Names'])) if zones['Names'][i] != 'Arena']
        self.start_analysis = False
        self.home = os.path.dirname(os.path.dirname(filename))
        self.video_title = os.path.splitext(os.path.basename(filename))[0]
        super().__init__(filename, remove_leading_singleton=True)
        
    def initialise_export_data(self):
        # Define the codec and create a video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        motion_path = os.path.join(self.home, "Motion_masks", self.video_title+".mp4")
        self.out = cv2.VideoWriter(motion_path, fourcc, self.frame_rate, (self.frame_width, self.frame_height), isColor=False)
        # Define an output file for the centre point data.
        df = pd.DataFrame(columns=['Frame number', 'X', 'Y', 'Zone'])
        self.data_path = os.path.join(self.home, "Center_point", self.video_title+'.csv')
        df.to_csv(self.data_path, index=False)
        
    def read_frame(self, frame_number):
        is_current_frame = frame_number == self.current_frame_pos
        if frame_number is not None and not is_current_frame:
            self._seek(frame_number)
        ret, frame = self._vr.read()
        return(ret, frame)
    
    def detect_rodent(self, frame):
        fgmask = self.fgbg.apply(frame, learningRate=-1)
        fgmask = cv2.GaussianBlur(fgmask, (5, 5), 0)
        ret, motion_mask = cv2.threshold(fgmask, self.threshold, 255, cv2.THRESH_BINARY)
        motion_mask = cv2.bitwise_and(motion_mask, self.zones['Masks'][self.arena_ind])
        motion_mask_bgr = cv2.merge((motion_mask, motion_mask, motion_mask))
        rodent_detection = cv2.addWeighted(frame, 1, motion_mask_bgr, 1, 0)
        return(motion_mask, rodent_detection)
    
    def find_centre_point(self, motion_mask, rodent_detection):
        M = cv2.moments(motion_mask)
        if M["m00"] == 0:
            cX = self.last_known_cX
            cY = self.last_known_cY
        else:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            self.last_known_cX = cX
            self.last_known_cY = cY
        centre_point = (cX, cY)
        cv2.circle(rodent_detection, centre_point, 6, (0, 0, 255), -1)
        return(centre_point, rodent_detection)
    
    def find_zone(self, centre_point):
        zone_list = []
        cX, cY = centre_point
        for i in self.ind_no_arena:
            val = (1 if self.zones['Masks'][i][cY][cX] == 255 else 0)
            if val == 1:
                zone_list += [self.zones['Names'][i]]
        zone_presence = ' '.join(zone_list)
        return(zone_presence)

    def read(self, frame_number=None):
        # Read the video frame.
        ret, frame = self.read_frame(frame_number)
        # Detect the rodent in the video.
        motion_mask, rodent_detection = self.detect_rodent(frame)
        # Find the centre point.
        centre_point, rodent_detection = self.find_centre_point(motion_mask, rodent_detection)
        # Find the zone presence.
        self.zone_presence = self.find_zone(centre_point)
        # Export the data for this frame.
        if self.start_analysis == True:
            cX, cY = centre_point
            df = pd.DataFrame({'Frame number':[frame_number], 'X':[cX], 'Y':[cY], 'Zone':[self.zone_presence]})
            df.to_csv(self.data_path, mode='a', index=False, header=False)
            self.out.write(motion_mask)
        
        return ret, rodent_detection
    
    def set_threshold(self, value):
        self.threshold = value
    
    # def annotate_zone_names_on_video(self):
    #     blank_frame = np.zeros((self.frame_height, self.frame_width), dtype=np.uint8)
    #     if len(zone_list) > 0:
    #         x,y = (0,0)
    #         text_size, _ = cv2.getTextSize(self.zone_presence, cv2.FONT_HERSHEY_SIMPLEX, 1, 1)
    #         text_w, text_h = text_size
    #         # Add the zones labels to the video with the real-time rodent detection.
    #         cv2.rectangle(rodent_detection, (x,y), (round((x+text_w)), round(y+text_h)), (255,255,255), -1)
    #         cv2.putText(rodent_detection, self.zone_presence, (x, y + text_h), 
    #                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    #         # Add the zones labels to blank frames, so they can be exported as a video.
    #         cv2.rectangle(blank_frame, (x,y), (round((x+text_w)), round(y+text_h)), (255,255,255), -1)
    #         cv2.putText(blank_frame, self.zone_presence, (x, y + text_h), 
    #                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)