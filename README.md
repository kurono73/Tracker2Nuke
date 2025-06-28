# Blender Addon: Tracker to Nuke

## Overview
**Tracker to Nuke** is a Blender addon that allows you to easily transfer 2D tracking data from Blender’s Movie Clip Editor to Nuke via copy and paste.  
It also supports copying and pasting lens distortion parameters in Nuke's default distortion model.

---

## Features

- Copy Blender’s 2D tracking data directly to Nuke's **Tracker Node** via clipboard.
- Supports full tracker export, selected trackers, pattern corners, and plane tracks.
- Transfers lens distortion parameters between Blender and Nuke using Nuke’s default distortion model (K1, K2).

---

## Location
- **Movie Clip Editor**  
  - `Sidebar > Track Tab > Tracker to Nuke`  
  - `Header > Tracker to Nuke`

---

## Tracker Export

When you copy tracking data, it is formatted for direct pasting into Nuke as a **Tracker Node**.

- **ALL**  
    Copies all trackers from the active Movie Clip to the clipboard.
  
- **Selected**  
    Copies only the selected trackers from the active Movie Clip.

- **Export Pattern Corners**  
    Copies the 4 corner positions of the selected track’s pattern area.

- **Export Plane Track**  
    Copies the 4 corner positions of the selected **Plane Track**.

>  **Note:**  
When using object tracking with multiple objects, the export will copy data from the active object.
Blender's lens distortion correction is not applied to the coordinate transformation of 2D tracking data.

---

## Lens Distortion

Allows lens distortion parameter exchange between Blender and Nuke’s default distortion model (K1, K2).

- **Copy**  
    Copies the lens distortion parameters of the Nuke model in the active clip to the clipboard. The copied data can be pasted directly as a LensDistortion Node in Nuke.

- **Paste**  
　　Select the LensDistortion Node in Nuke and copy it to the clipboard.
    Pastes lens distortion parameters from the clipboard into Blender. If the lens distortion model is not set to "Nuke" in Blender, it will be automatically switched.

---

