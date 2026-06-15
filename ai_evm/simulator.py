import cv2
import numpy as np
import time
from datetime import datetime

def get_simulated_frame(phase_key, session_dict):
    # Standard dimensions for the webcam feed
    width, height = 640, 480
    
    # 1. Create a dark tech dashboard canvas (BGR format)
    # Slate dark background: (30, 20, 15) in BGR (very dark navy/slate)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (24, 18, 13)
    
    # Draw faint grid lines to give a high-tech vibe
    grid_size = 40
    for y in range(0, height, grid_size):
        cv2.line(img, (0, y), (width, y), (38, 30, 22), 1)
    for x in range(0, width, grid_size):
        cv2.line(img, (x, 0), (x, height), (38, 30, 22), 1)
        
    # 2. Draw HUD Corners (Light neon blue/cyan)
    hud_color = (255, 200, 0) # Cyan in BGR
    bracket_len = 25
    thickness = 2
    
    # Top Left
    cv2.line(img, (15, 15), (15 + bracket_len, 15), hud_color, thickness)
    cv2.line(img, (15, 15), (15, 15 + bracket_len), hud_color, thickness)
    # Top Right
    cv2.line(img, (width - 15, 15), (width - 15 - bracket_len, 15), hud_color, thickness)
    cv2.line(img, (width - 15, 15), (width - 15, 15 + bracket_len), hud_color, thickness)
    # Bottom Left
    cv2.line(img, (15, height - 15), (15 + bracket_len, height - 15), hud_color, thickness)
    cv2.line(img, (15, height - 15), (15, height - 15 - bracket_len), hud_color, thickness)
    # Bottom Right
    cv2.line(img, (width - 15, height - 15), (width - 15 - bracket_len, height - 15), hud_color, thickness)
    cv2.line(img, (width - 15, height - 15), (width - 15, height - 15 - bracket_len), hud_color, thickness)

    # 3. Draw Blinking "REC" Indicator
    timestamp = time.time()
    if int(timestamp * 2) % 2 == 0:
        cv2.circle(img, (35, 35), 6, (0, 0, 255), -1) # Red dot
    else:
        cv2.circle(img, (35, 35), 6, (40, 40, 60), -1) # Faded dot
    cv2.putText(img, "LIVE FEED (SIMULATED)", (50, 41), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

    # 4. Display system timestamp and stats
    t_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(img, t_str, (width - 180, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)
    cv2.putText(img, "MODE: FALLBACK  RES: 640x480", (width - 245, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

    # 5. Draw dynamic laser scanning line
    # Calculate animated scanning line position using sine wave
    scan_y = int((np.sin(timestamp * 2) + 1.0) / 2.0 * (height - 60)) + 30
    # Semi-transparent overlay for scanner line glow
    overlay = img.copy()
    cv2.line(overlay, (20, scan_y), (width - 20, scan_y), (0, 255, 0), 2)
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)

    # 6. Render phase-specific simulation UI
    if phase_key == 'phase_1':
        persons = int(session_dict.get('sim_persons', 1))
        
        if persons == 1:
            # Draw 1 green bounding box representing a voter
            cv2.rectangle(img, (220, 100), (420, 380), (0, 255, 0), 2)
            cv2.putText(img, "person: 98.6%", (220, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Status Text
            cv2.putText(img, "STATUS: 1 PERSON DETECTED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(img, "VERIFICATION: READY (1 Voter present)", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        elif persons == 2:
            # Draw 2 bounding boxes (Violation!)
            cv2.rectangle(img, (110, 100), (290, 380), (0, 0, 255), 2)
            cv2.putText(img, "person: 97.4%", (110, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            cv2.rectangle(img, (330, 100), (510, 380), (0, 0, 255), 2)
            cv2.putText(img, "person: 95.2%", (330, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # Status Text
            cv2.putText(img, "STATUS: MULTIPLE PEOPLE DETECTED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(img, "VERIFICATION: BLOCKED (Max 1 Voter)", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        else:
            # 0 Persons
            cv2.putText(img, "STATUS: NO VOTERS DETECTED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            cv2.putText(img, "VERIFICATION: WAITING...", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    elif phase_key == 'phase_2':
        has_mask = session_dict.get('sim_has_mask', False)
        
        # Draw face detection box
        cv2.rectangle(img, (220, 100), (420, 340), (0, 255, 0), 2)
        cv2.putText(img, "face: 99.4%", (220, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        if has_mask:
            # Draw red mask overlay box
            cv2.rectangle(img, (250, 210), (390, 310), (0, 0, 255), 2)
            cv2.putText(img, "mask: 98.9%", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            cv2.putText(img, "STATUS: MASK DETECTED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(img, "VERIFICATION: BLOCKED (Please remove mask)", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        else:
            # Draw green "no mask" text
            cv2.putText(img, "No Mask detected", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            cv2.putText(img, "STATUS: NO MASK DETECTED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(img, "VERIFICATION: READY", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    elif phase_key == 'phase_3' or phase_key == 'detect_face':
        face_name = session_dict.get('sim_face_name', 'Satyendra')
        
        if face_name == 'Unknown':
            cv2.rectangle(img, (220, 100), (420, 340), (0, 0, 255), 2)
            cv2.putText(img, "face: Unknown", (220, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            cv2.putText(img, "IDENTITY: UNVERIFIED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(img, "NOMINATION NOT FOUND IN CONSTITUENCY", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        else:
            cv2.rectangle(img, (220, 100), (420, 340), (0, 255, 0), 2)
            cv2.putText(img, f"face: {face_name}", (220, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Match info box
            cv2.putText(img, f"NAME: {face_name}", (220, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            cv2.putText(img, "ROLE: REGISTERED VOTER", (220, 395), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            cv2.putText(img, "IDENTITY: VERIFIED", (40, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(img, "ACCESS GRANTED TO EVM SYSTEM", (40, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # Encode frame to JPEG
    ret, jpeg = cv2.imencode('.jpg', img)
    return jpeg.tobytes()
