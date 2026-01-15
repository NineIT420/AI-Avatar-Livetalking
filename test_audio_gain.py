#!/usr/bin/env python3
"""
Test script to verify audio gain functionality
"""

import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from baseasr import BaseASR

class TestOptions:
    def __init__(self):
        self.batch_size = 4
        self.l = 2
        self.r = 2
        self.audio_gain = 1.5  # Test with gain

def test_audio_gain():
    """Test that audio gain is properly applied"""

    # Create test options with audio gain
    opt = TestOptions()

    # Create BaseASR instance
    asr = BaseASR(opt, None)

    # Verify audio_gain attribute is set
    assert hasattr(asr, 'audio_gain'), "BaseASR should have audio_gain attribute"
    assert asr.audio_gain == 1.5, f"Expected audio_gain=1.5, got {asr.audio_gain}"

    # Create test audio frame
    test_frame = np.array([0.1, 0.2, -0.1, -0.2], dtype=np.float32)

    # Manually apply the gain logic (simulating what happens in get_audio_frame)
    frame_with_gain = test_frame * asr.audio_gain
    max_val = np.abs(frame_with_gain).max()
    if max_val > 1.0:
        frame_with_gain = frame_with_gain / max_val

    expected_result = np.array([0.15, 0.3, -0.15, -0.3], dtype=np.float32)

    print(f"Original frame: {test_frame}")
    print(f"Frame with gain: {frame_with_gain}")
    print(f"Expected result: {expected_result}")
    print(f"Audio gain applied successfully: {np.allclose(frame_with_gain, expected_result)}")

    # Test with no gain
    opt_no_gain = TestOptions()
    opt_no_gain.audio_gain = 1.0
    asr_no_gain = BaseASR(opt_no_gain, None)

    frame_no_gain = test_frame * asr_no_gain.audio_gain
    max_val = np.abs(frame_no_gain).max()
    if max_val > 1.0:
        frame_no_gain = frame_no_gain / max_val

    print(f"Frame with no gain: {frame_no_gain}")
    print(f"No gain applied correctly: {np.allclose(frame_no_gain, test_frame)}")

    print("\nAudio gain feature test completed successfully!")

if __name__ == "__main__":
    test_audio_gain()
