# Fractured

Fractured is a 3D action adventure set in two connected realities, Nova and Veyra. The canal crossing is the current playable slice: explore the Nova transit station, cross between the cities, recover the echo, and return to the fracture.

## Play the full story (Scenes 1–8)

**Play in the browser:** https://kaazkayy05.github.io/Fractured/ (built from the `gh-pages` branch).

Or open the **root** `project.godot` in Godot 4.7.2 (after `git lfs pull`) and press F5. The game runs the whole scene breakdown in order: Research Facility, City Streets, Transit Station, Central Reactor, then the merged city and credits. City Streets uses web-weight copies of the team's Nova/Veyra city meshes (`cities/`), made from `playtest/worlds/` by `art/scripts/build_city_web.py`.

To rebuild the browser version: Project → Export → Web, which writes `build/web/`. Then publish that folder to the `gh-pages` branch.

| Key | Action | Unlocked in |
| --- | --- | --- |
| WASD / Space / Shift / Mouse | Move, jump, sprint, look (Esc frees the mouse) | Scene 1 |
| E | Interact; hold E on power and convergence nodes | Scene 1 |
| Q / F | Reality Shift / Fracture Burst | Scene 2 |
| LMB / RMB | Attack combo / Guard (guard just before a hit to counter) | Scene 3 |
| C / V | Echo Projection / Rift Recall | Scene 3 |
| E / G | Structural Manipulation (unstable structures) / Chain Reaction | Scene 4 |
| F9 | Skip to the next scene (testing) | any |

To start at a given scene, run `Godot --path . -- --scene=4`. Win by merging the realities in Scene 7. You lose if health reaches 0 or instability hits the critical limit during the final encounter. Retry restarts from the current scene.

The code follows the architecture diagram, one script per box in `scripts/`:

- `Main.gd` handles scene progression.
- Location scenes (`ResearchFacility`, `CityStreets`, `TransitStation`, `CentralReactor`) extend `Location.gd`.
- Player components: `Player`, `RealityShift`, `FractureEnergy`, `Combat`, `DefensiveCounter`, `EchoProjection`, `ChainReaction`.
- World scripts: `Structure`, `EnemyAI`.
- `RealityManager` and `InstabilityManager` are autoloads.
- Rooms are the exported `.glb` files in `export/`, and their Blender sources are in `art/source/`.

`tests/Playthrough.tscn` drives Scenes 1–8 automatically and checks that every objective point stands on real floor:

```
Godot --headless --path . res://tests/Playthrough.tscn
```

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
