import numpy as np
import cv2
import copy

def get_image_blending(image,face,face_box,mask_array,crop_box):
    body = image.copy()
    x, y, x1, y1 = face_box
    x_s, y_s, x_e, y_e = crop_box
    
    frame_h, frame_w = body.shape[:2]
    x_s = max(0, min(int(x_s), frame_w - 1))
    y_s = max(0, min(int(y_s), frame_h - 1))
    x_e = max(x_s + 1, min(int(x_e), frame_w))
    y_e = max(y_s + 1, min(int(y_e), frame_h))
    
    x = max(x_s, min(int(x), x_e - 1))
    y = max(y_s, min(int(y), y_e - 1))
    x1 = max(x + 1, min(int(x1), x_e))
    y1 = max(y + 1, min(int(y1), y_e))
    
    crop_w = x_e - x_s
    crop_h = y_e - y_s
    if crop_w <= 0 or crop_h <= 0:
        return body
    
    try:
        face_large = copy.deepcopy(body[y_s:y_e, x_s:x_e])
        
        face_h, face_w = face.shape[:2]
        target_h = y1 - y
        target_w = x1 - x
        
        if target_h > 0 and target_w > 0 and face_h > 0 and face_w > 0:
            if face_h != target_h or face_w != target_w:
                face = cv2.resize(face, (target_w, target_h))
            face_large[y-y_s:y1-y_s, x-x_s:x1-x_s] = face

        mask_image = cv2.cvtColor(mask_array, cv2.COLOR_BGR2GRAY) if len(mask_array.shape) == 3 else mask_array
        mask_image = (mask_image/255).astype(np.float32)
        
        mask_h, mask_w = mask_image.shape[:2]
        if mask_h != crop_h or mask_w != crop_w:
            mask_image = cv2.resize(mask_image, (crop_w, crop_h))
        
        crop_region = body[y_s:y_e, x_s:x_e]
        
        if (face_large.shape[:2] == crop_region.shape[:2] == mask_image.shape[:2] and
            len(face_large.shape) == len(crop_region.shape)):
            try:
                body[y_s:y_e, x_s:x_e] = cv2.blendLinear(face_large, crop_region, mask_image, 1-mask_image)
            except cv2.error as e:
                import logging
                logging.getLogger(__name__).warning(f"MuseTalk: blendLinear failed: {e}. Using simple paste.")
                body[y_s:y_e, x_s:x_e] = face_large
        else:
            body[y_s:y_e, x_s:x_e] = face_large
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"MuseTalk: Error in get_image_blending: {e}. Returning original frame.")
        return body

    return body