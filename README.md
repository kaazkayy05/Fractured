# Fractured

Fractured is a 3D action adventure set in two connected realities, Nova and Veyra. The canal crossing is the current playable slice: explore the Nova transit station, cross between the cities, recover the echo, and return to the fracture.

## Play the crossing

Install Git LFS before cloning, or run `git lfs pull` in an existing clone. Open `playtest/project.godot` in Godot 4.7.2, let the city meshes import, and press F5.

## Hali's mechanics in the crossing

- **Q — Reality Shift:** Switch between Nova and Veyra in place, with a 3 second cooldown. The shift preserves movement momentum and adds 5 instability. If the destination is blocked, the player moves to the nearest safe spot.
- **Left click — Attack:** A successful hit on an enemy or fracture target grants 5 Fracture Energy, up to 100. Stationary fracture targets in the crossing make the energy loop testable before combat is added.
- **F — Fracture Burst:** Spend 40 energy to deal 25 damage within 4 meters. Burst cooldown is 5 seconds and each burst adds 15 instability. The integration supports damageable enemies and unstable structures that expose `take_damage` or `apply_damage`; enemies can expose `interrupt_attack` for the burst interrupt.
- Shifting at 60 or higher instability grants 10 additional Fracture Energy. If instability does not rise for 10 seconds, it decays by 1 point every 3 seconds.

The objective flow now asks the player to shift into the reality required for each route step. Q controls the world change; interacting with the route marker no longer shifts realities automatically.

## Project files

- `playtest/`: Godot Compatibility renderer scene, crossing controller, and Nova/Veyra city meshes
- `interiors/`: transit station blockout, Blender source, production scripts, and review renders

The current slice is built from the team's scenery work. Story locations beyond the canal crossing and final art polish remain future work.
