# Image-quality calibration

SpatialForge analyses a bounded 1600-pixel grayscale representation so focus scores are
comparable across common smartphone resolutions without loading every full-resolution image at
once. When OpenCV is installed, the focus score combines variance of Laplacian and Tenengrad;
feature density is the number of ORB keypoints detected with a 5,000-point cap. A deterministic
Pillow edge-density fallback keeps basic validation available without the optional vision wheel.

The current 100-point blur review threshold is a conservative screening value, not a camera
quality claim. Regression fixtures verify that a synthetically defocused capture ranks materially
below its sharp source. Release calibration must additionally sample legal, redistributable phone
captures across supported resolutions, indoor lighting, repeated texture, blank walls, and motion
blur. Threshold changes require fixture evidence and must not automatically exclude or delete an
image.

Exposure tests cover severe under/overexposure, clipped highlights, and low dynamic range.
Perceptual duplicate grouping uses connected components so transitive groups remain together.
Feature counts are explicitly presented as estimates and do not guarantee registration.
