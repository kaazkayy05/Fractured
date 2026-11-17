# Fractured

A Godot 4.7 prototype focused on Hali's mechanics, using the Compatibility renderer for web builds.

## Run

Open this folder in Godot and run the project. The current scene is a small graybox arena for practicing Hali's Reality Shift and Fracture Energy mechanics. The larger story locations and final art are future work.

## Controls

- WASD / arrows: move; mouse: camera; Space: jump; Esc: release mouse
- Q: Reality Shift; 3 second cooldown, preserves health and momentum, adds 5 instability
- H or left mouse: attack a visible target; a successful hit grants 5 energy
- F: Fracture Burst; costs 40 energy, 5 second cooldown, deals 25 damage within 4 meters, adds 15 instability

Energy holds up to 100. A shift at 60 or higher instability adds 10 energy. Instability decreases by 1 every 3 seconds after 10 seconds without an increase. Training targets are stationary props for charging and testing the burst.

## Files

- `systems/core/`: Hali mechanics integration, graybox arena, and HUD
- `systems/player/`: third-person movement and camera

The arena uses primitive meshes as placeholders. Story scenes, production art, and final effects are not included in this starter build.
